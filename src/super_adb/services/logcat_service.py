from __future__ import annotations

import queue
import shutil
import subprocess
import threading
import time
from collections import deque
from collections.abc import Callable
from typing import Protocol

from super_adb.services.errors import AdbError, AdbNotFoundError, AdbTimeoutError

OnBatch = Callable[[list[str]], None]
OnEnd = Callable[[int, str | None], None]


class StreamHandle(Protocol):
    def stop(self) -> None:
        """Stop this stream without affecting other ADB operations."""


class LogcatService(Protocol):
    def start_stream(self, serial: str, on_batch: OnBatch, on_end: OnEnd) -> StreamHandle:
        """Start a batched threadtime stream for one device."""

    def dump(self, serial: str, count: int) -> list[str]:
        """Return the most recent threadtime lines."""

    def clear_buffer(self, serial: str) -> None:
        """Clear the device logcat buffers."""

    def close(self) -> None:
        """Stop all streams and release service resources."""


class CancelToken:
    def __init__(self) -> None:
        self._event = threading.Event()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def cancel(self) -> None:
        self._event.set()

    def wait(self, timeout: float | None = None) -> bool:
        return self._event.wait(timeout)


class _StreamHandle:
    def __init__(
        self,
        serial: str,
        on_batch: OnBatch,
        on_end: OnEnd,
    ) -> None:
        self.serial = serial
        self.on_batch = on_batch
        self.on_end = on_end
        self.cancel_token = CancelToken()
        self._process_lock = threading.Lock()
        self._process: subprocess.Popen[str] | None = None
        self._thread: threading.Thread | None = None
        self._done = threading.Event()

    def stop(self) -> None:
        self.cancel_token.cancel()
        self._terminate_current()

    def _attach_process(self, process: subprocess.Popen[str]) -> None:
        with self._process_lock:
            self._process = process
            cancelled = self.cancel_token.cancelled
        if cancelled:
            self._terminate(process)

    def _detach_process(self, process: subprocess.Popen[str]) -> None:
        with self._process_lock:
            if self._process is process:
                self._process = None

    def _terminate_current(self) -> None:
        with self._process_lock:
            process = self._process
        if process is not None:
            self._terminate(process)

    @staticmethod
    def _terminate(process: subprocess.Popen[str]) -> None:
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


class SubprocessLogcatService:
    _BATCH_INTERVAL_SECONDS = 0.05
    _BATCH_MAX_LINES = 500
    _STARTUP_ERROR_GRACE_SECONDS = 0.2

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._streams: dict[str, _StreamHandle] = {}
        self._closed = False

    def start_stream(self, serial: str, on_batch: OnBatch, on_end: OnEnd) -> StreamHandle:
        adb = self._find_adb()
        with self._lock:
            if self._closed:
                raise AdbError("Service logcat sudah ditutup.")
            if serial in self._streams:
                raise AdbError(f"Aliran logcat untuk perangkat {serial} sudah berjalan.")
            handle = _StreamHandle(serial, on_batch, on_end)
            self._streams[serial] = handle
            thread = threading.Thread(
                target=self._run_stream,
                args=(handle, adb),
                name=f"logcat-{serial}",
                daemon=True,
            )
            handle._thread = thread
            try:
                thread.start()
            except RuntimeError:
                del self._streams[serial]
                raise
        return handle

    def dump(self, serial: str, count: int) -> list[str]:
        if isinstance(count, bool) or not 1 <= count <= 20000:
            raise ValueError("Jumlah baris logcat harus antara 1 dan 20000.")
        command = [
            self._find_adb(),
            "-s",
            serial,
            "logcat",
            "-d",
            "-v",
            "threadtime",
            "-t",
            str(count),
        ]
        return self._run_command(command, timeout=20.0)

    def clear_buffer(self, serial: str) -> None:
        command = [self._find_adb(), "-s", serial, "logcat", "-c"]
        self._run_command(command, timeout=10.0)

    def close(self) -> None:
        with self._lock:
            self._closed = True
            streams = tuple(self._streams.values())
        for handle in streams:
            handle.stop()
        for handle in streams:
            thread = handle._thread
            if thread is not None:
                thread.join(timeout=2)

    @staticmethod
    def _find_adb() -> str:
        adb = shutil.which("adb")
        if adb is None:
            raise AdbNotFoundError(
                "ADB tidak ditemukan. Pasang Android Platform Tools dan tambahkan adb ke PATH."
            )
        return adb

    def _run_command(self, command: list[str], timeout: float) -> list[str]:
        try:
            completed = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except subprocess.TimeoutExpired:
            raise AdbTimeoutError(
                f"Perintah {' '.join(command)} melewati batas waktu {timeout:g} detik."
            ) from None
        except FileNotFoundError as error:
            raise AdbNotFoundError(
                "ADB tidak ditemukan. Pasang Android Platform Tools dan tambahkan adb ke PATH."
            ) from error
        except OSError as error:
            raise AdbError(f"Gagal menjalankan ADB: {error}") from error
        output = completed.stdout or ""
        if completed.returncode != 0:
            detail = output.strip()
            if detail:
                raise AdbError(f"Perintah logcat gagal (kode {completed.returncode}): {detail}")
            raise AdbError(f"Perintah logcat gagal dengan kode {completed.returncode}.")
        return output.splitlines()

    def _run_stream(self, handle: _StreamHandle, adb: str) -> None:
        returncode = -1
        message: str | None = None
        output_tail: deque[str] = deque(maxlen=20)
        command = [adb, "-s", handle.serial, "logcat", "-v", "threadtime", "-T", "500"]
        try:
            while not handle.cancel_token.cancelled:
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                handle._attach_process(process)
                try:
                    returncode, output_tail, retry_without_since = self._consume_stream(
                        process,
                        handle,
                        command_has_since="-T" in command,
                        output_tail=output_tail,
                    )
                finally:
                    handle._detach_process(process)
                if retry_without_since and not handle.cancel_token.cancelled:
                    command = command[:-2]
                    continue
                break
            if handle.cancel_token.cancelled:
                message = None
            else:
                message = self._end_message(returncode, output_tail)
        except Exception as error:
            message = f"Gagal menjalankan logcat: {error}"
            handle._terminate_current()
        finally:
            handle._done.set()
            self._remove_stream(handle)
            handle.on_end(returncode, message)

    def _consume_stream(
        self,
        process: subprocess.Popen[str],
        handle: _StreamHandle,
        *,
        command_has_since: bool,
        output_tail: deque[str],
    ) -> tuple[int, deque[str], bool]:
        stdout = process.stdout
        if stdout is None:
            raise AdbError("Output logcat tidak dapat dibaca.")
        lines: queue.Queue[str | None] = queue.Queue()

        def read_output() -> None:
            try:
                for line in stdout:
                    lines.put(line.rstrip("\r\n"))
            finally:
                lines.put(None)

        reader = threading.Thread(target=read_output, name="logcat-output", daemon=True)
        reader.start()
        batch: list[str] = []
        pending: list[str] = []
        suspect_since_error = False
        suspect_started_at: float | None = None
        started = False
        last_flush = time.monotonic()

        def flush() -> None:
            nonlocal last_flush
            if batch:
                handle.on_batch(batch.copy())
                batch.clear()
                last_flush = time.monotonic()

        def accept_pending() -> None:
            nonlocal started
            started = True
            batch.extend(pending)
            pending.clear()
            if len(batch) >= self._BATCH_MAX_LINES:
                flush()

        retry = False
        while True:
            try:
                line = lines.get(timeout=self._BATCH_INTERVAL_SECONDS)
                received_line = line is not None
            except queue.Empty:
                line = None
                received_line = False

            now = time.monotonic()
            if received_line and line is not None:
                output_tail.append(line)
                if not started:
                    pending.append(line)
                    if self._looks_like_unsupported_since(line):
                        suspect_since_error = True
                        suspect_started_at = now
                    elif not suspect_since_error:
                        accept_pending()
                else:
                    batch.append(line)
            elif suspect_since_error and suspect_started_at is not None:
                if process.poll() is not None:
                    returncode = process.wait()
                    retry = command_has_since and returncode != 0
                    if retry:
                        pending.clear()
                        break
                    accept_pending()
                elif now - suspect_started_at >= self._STARTUP_ERROR_GRACE_SECONDS:
                    accept_pending()

            if handle.cancel_token.cancelled:
                handle._terminate_current()
            if batch and (
                len(batch) >= self._BATCH_MAX_LINES
                or now - last_flush >= self._BATCH_INTERVAL_SECONDS
            ):
                flush()

            if received_line:
                continue
            if lines.empty() and process.poll() is not None:
                break
            if line is None and not received_line:
                continue

        returncode = process.wait()
        if pending and not retry:
            accept_pending()
        flush()
        reader.join(timeout=1)
        return returncode, output_tail, retry

    @staticmethod
    def _looks_like_unsupported_since(line: str) -> bool:
        lowered = line.casefold()
        option_error = any(
            phrase in lowered for phrase in ("invalid option", "unknown option", "unrecognized")
        )
        return option_error and ("-t" in lowered or "option -- t" in lowered)

    @staticmethod
    def _end_message(returncode: int, output_tail: deque[str]) -> str:
        detail = "\n".join(output_tail).casefold()
        if "device offline" in detail:
            return "Dihentikan: perangkat ADB offline."
        if "device unauthorized" in detail:
            return "Dihentikan: perangkat ADB belum diotorisasi."
        if "device not found" in detail or "no devices/emulators" in detail:
            return "Dihentikan: perangkat terputus dari ADB."
        if returncode == 0:
            return "Aliran logcat berakhir."
        output = "\n".join(output_tail).strip()
        if output:
            return f"Aliran logcat terputus (kode {returncode}): {output}"
        return f"Aliran logcat terputus (kode {returncode})."

    def _remove_stream(self, handle: _StreamHandle) -> None:
        with self._lock:
            if self._streams.get(handle.serial) is handle:
                del self._streams[handle.serial]
