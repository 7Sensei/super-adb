from __future__ import annotations

import queue
import re
import shutil
import subprocess
import threading
import time
from collections.abc import Callable, Iterator
from typing import Protocol

from super_adb.models.device_info import DeviceInfo
from super_adb.services.errors import AdbError, AdbNotFoundError, AdbTimeoutError


class AdbService(Protocol):
    def execute(
        self,
        command: list[str],
        on_line: Callable[[str], None],
        timeout: float | None = None,
    ) -> str:
        """Run an ADB command, stream output lines, and return the complete output."""

    def get_device_info(self, serial: str) -> DeviceInfo:
        """Return available device properties; unavailable fields remain unset."""

    def close(self) -> None:
        """Stop active ADB processes and release service resources."""


class SubprocessAdbService:
    def __init__(self, command_timeout: float = 15.0) -> None:
        if command_timeout <= 0:
            raise ValueError("command_timeout harus lebih besar dari nol.")
        self._command_timeout = command_timeout
        self._process_lock = threading.Lock()
        self._active_processes: set[subprocess.Popen[str]] = set()
        self._closed = False

    def execute(
        self,
        command: list[str],
        on_line: Callable[[str], None],
        timeout: float | None = None,
    ) -> str:
        if not isinstance(command, list) or not all(isinstance(part, str) for part in command):
            raise AdbError("Perintah ADB harus berupa list[str].")
        if not command or command[0] != "adb":
            raise AdbError("Perintah harus diawali dengan 'adb'.")

        executable = shutil.which("adb")
        if executable is None:
            raise AdbNotFoundError(
                "ADB tidak ditemukan. Pasang Android Platform Tools dan tambahkan adb ke PATH."
            )

        process: subprocess.Popen[str] | None = None
        try:
            with self._process_lock:
                if self._closed:
                    raise AdbError("Service ADB sudah ditutup.")
                process = subprocess.Popen(
                    [executable, *command[1:]],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                self._active_processes.add(process)

            with process:
                if process.stdout is None:
                    raise AdbError("Output ADB tidak dapat dibaca.")

                output_lines: list[str] = []
                timeout = self._timeout_for_command(command) if timeout is None else timeout
                deadline = time.monotonic() + timeout if timeout is not None else None
                for raw_line in self._read_lines(process, command, deadline):
                    line = raw_line.rstrip("\r\n")
                    output_lines.append(line)
                    on_line(line)
                if deadline is None:
                    returncode = process.wait()
                else:
                    remaining = deadline - time.monotonic()
                    try:
                        returncode = process.wait(timeout=max(remaining, 0))
                    except subprocess.TimeoutExpired:
                        self._stop_process(process)
                        raise AdbTimeoutError(
                            self._timeout_message(command, self._command_timeout)
                        ) from None
        except FileNotFoundError as error:
            raise AdbNotFoundError(
                "ADB tidak ditemukan. Pasang Android Platform Tools dan tambahkan adb ke PATH."
            ) from error
        except OSError as error:
            raise AdbError(f"Gagal menjalankan ADB: {error}") from error
        finally:
            if process is not None:
                with self._process_lock:
                    self._active_processes.discard(process)

        output = "\n".join(output_lines)
        if returncode != 0:
            raise AdbError(self._failure_message(output, returncode))
        if "device offline" in output.lower():
            raise AdbError("Perangkat ADB sedang offline. Hubungkan ulang perangkat.")
        if "device unauthorized" in output.lower():
            raise AdbError(
                "Perangkat ADB belum diotorisasi. Setujui dialog USB debugging pada perangkat."
            )
        return output

    @staticmethod
    def _failure_message(output: str, returncode: int) -> str:
        lowered = output.lower()
        if "device offline" in lowered:
            return "Perangkat ADB sedang offline. Hubungkan ulang perangkat."
        if "device unauthorized" in lowered:
            return "Perangkat ADB belum diotorisasi. Setujui dialog USB debugging pada perangkat."
        detail = output.strip()
        if detail:
            return f"Perintah ADB gagal (kode {returncode}): {detail}"
        return f"Perintah ADB gagal dengan kode {returncode}."

    def _timeout_for_command(self, command: list[str]) -> float | None:
        if command[1:2] in (["devices"], ["connect"]):
            return self._command_timeout
        return None

    def get_device_info(self, serial: str) -> DeviceInfo:
        def read(*arguments: str) -> str | None:
            try:
                return self.execute(
                    ["adb", "-s", serial, *arguments],
                    lambda line: None,
                    timeout=8.0,
                )
            except AdbError:
                return None

        def property_value(name: str) -> str | None:
            value = read("shell", "getprop", name)
            return value.strip() if value and value.strip() else None

        brand = property_value("ro.product.brand")
        model = property_value("ro.product.model")
        product_name = property_value("ro.product.name")
        android_version = property_value("ro.build.version.release")
        api_level = self._parse_int(property_value("ro.build.version.sdk"))
        chipset = property_value("ro.board.platform")
        cpu_abi = property_value("ro.product.cpu.abi")

        screen_output = read("shell", "wm", "size")
        sizes = re.findall(r"(?:Physical|Override) size:\s*(\d+)x(\d+)", screen_output or "")
        screen_w, screen_h = map(int, sizes[-1]) if sizes else (None, None)

        density_output = read("shell", "wm", "density")
        densities = re.findall(r"(?:Physical|Override) density:\s*(\d+)", density_output or "")
        density = int(densities[-1]) if densities else None

        memory_output = read("shell", "cat", "/proc/meminfo")
        memory_match = re.search(r"MemTotal:\s*(\d+)\s*kB", memory_output or "")
        ram_gb = round(int(memory_match.group(1)) / 1024 / 1024, 2) if memory_match else None

        battery_output = read("shell", "dumpsys", "battery")
        battery_level = self._parse_int(self._find_value(battery_output, r"^\s*level:\s*(\d+)"))
        battery_status = self._parse_int(self._find_value(battery_output, r"^\s*status:\s*(\d+)"))

        return DeviceInfo(
            serial=serial,
            state="device",
            brand=brand,
            model=model,
            product_name=product_name,
            android_version=android_version,
            api_level=api_level,
            chipset=chipset,
            cpu_abi=cpu_abi,
            screen_w=screen_w,
            screen_h=screen_h,
            density=density,
            ram_gb=ram_gb,
            battery_level=battery_level,
            charging=(battery_status == 2) if battery_status is not None else None,
        )

    @staticmethod
    def _find_value(output: str | None, pattern: str) -> str | None:
        match = re.search(pattern, output or "", re.MULTILINE)
        return match.group(1) if match else None

    @staticmethod
    def _parse_int(value: str | None) -> int | None:
        try:
            return int(value) if value is not None else None
        except ValueError:
            return None

    def _read_lines(
        self,
        process: subprocess.Popen[str],
        command: list[str],
        deadline: float | None,
    ) -> Iterator[str]:
        stdout = process.stdout
        if stdout is None:
            raise AdbError("Output ADB tidak dapat dibaca.")
        if deadline is None:
            yield from stdout
            return

        lines: queue.Queue[str | None] = queue.Queue()

        def read_output() -> None:
            try:
                for line in stdout:
                    lines.put(line)
            finally:
                lines.put(None)

        reader = threading.Thread(target=read_output, name="adb-output", daemon=True)
        reader.start()
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self._stop_process(process)
                raise AdbTimeoutError(self._timeout_message(command, self._command_timeout))
            try:
                line = lines.get(timeout=remaining)
            except queue.Empty:
                self._stop_process(process)
                raise AdbTimeoutError(
                    self._timeout_message(command, self._command_timeout)
                ) from None
            if line is None:
                return
            yield line

    @staticmethod
    def _timeout_message(command: list[str], timeout: float) -> str:
        return (
            f"Perintah {' '.join(command)} melewati batas waktu {timeout:g} detik; "
            "proses dihentikan."
        )

    def close(self) -> None:
        with self._process_lock:
            self._closed = True
            processes = tuple(self._active_processes)

        for process in processes:
            self._stop_process(process)

    @staticmethod
    def _stop_process(process: subprocess.Popen[str]) -> None:
        if process.poll() is not None:
            return
        try:
            process.terminate()
        except OSError:
            if process.poll() is None:
                raise
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
