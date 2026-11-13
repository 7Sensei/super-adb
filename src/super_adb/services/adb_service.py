from __future__ import annotations

import shutil
import subprocess
import threading
from collections.abc import Callable
from typing import Protocol

from super_adb.services.errors import AdbError, AdbNotFoundError


class AdbService(Protocol):
    def execute(self, command: list[str], on_line: Callable[[str], None]) -> str:
        """Run an ADB command, stream output lines, and return the complete output."""


class SubprocessAdbService:
    def __init__(self) -> None:
        self._process_lock = threading.Lock()
        self._active_processes: set[subprocess.Popen[str]] = set()
        self._closed = False

    def execute(self, command: list[str], on_line: Callable[[str], None]) -> str:
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
                for raw_line in process.stdout:
                    line = raw_line.rstrip("\r\n")
                    output_lines.append(line)
                    on_line(line)
                returncode = process.wait()
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
