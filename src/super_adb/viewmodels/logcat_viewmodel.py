from __future__ import annotations

from collections import deque
from collections.abc import Callable
from concurrent.futures import Executor, Future, ThreadPoolExecutor
from pathlib import Path

from super_adb.models.logcat_entry import LogcatEntry
from super_adb.services.errors import AdbError
from super_adb.services.logcat_parser import LogcatParser
from super_adb.services.logcat_service import LogcatService, StreamHandle
from super_adb.viewmodels.base import Observable, Signal
from super_adb.viewmodels.ports import UiDispatcher

_LEVEL_ORDER = ("V", "D", "I", "W", "E", "F")
_RING_BUFFER_SIZE = 50_000


class LogcatViewModel:
    def __init__(
        self,
        service: LogcatService,
        selected_serial: Observable[str | None],
        dispatcher: UiDispatcher,
        lifecycle_events: Signal[str] | None = None,
        executor: Executor | None = None,
    ) -> None:
        self._service = service
        self._selected_serial = selected_serial
        self._dispatcher = dispatcher
        self._executor = executor or ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="super-adb-logcat"
        )
        self._owns_executor = executor is None

        self.running = Observable(False)
        self.status = Observable("Siap")
        self.min_level = Observable("V")
        self.tag_query = Observable("")
        self.text_query = Observable("")
        self.paused = Observable(False)
        self.total_count = Observable(0)
        self.visible_count = Observable(0)
        self.batch_appended: Signal[list[LogcatEntry]] = Signal()
        self.reset: Signal[None] = Signal()

        self._entries: deque[LogcatEntry] = deque()
        self._visible: deque[LogcatEntry] = deque()
        self._parser = LogcatParser()
        self._stream_handle: StreamHandle | None = None
        self._stream_serial: str | None = None
        self._generation = 0
        self._ended_generation: int | None = None
        self._stop_reason: str | None = None
        self._stop_requested_generation: int | None = None
        self._closed = False

        self._unsubscribers: list[Callable[[], None]] = [
            selected_serial.subscribe(self._selected_serial_changed),
            self.min_level.subscribe(lambda _: self._rebuild_visible()),
            self.tag_query.subscribe(lambda _: self._rebuild_visible()),
            self.text_query.subscribe(lambda _: self._rebuild_visible()),
            self.paused.subscribe(self._paused_changed),
        ]
        if lifecycle_events is not None:
            self._unsubscribers.append(lifecycle_events.connect(self._lifecycle_event))

    def start(self) -> None:
        if self._closed:
            self.status.value = "Service logcat sudah ditutup."
            return
        if self.running.value:
            return
        serial = self._selected_serial.value
        if serial is None:
            self.status.value = "Pilih perangkat ADB terlebih dahulu."
            return

        self._generation += 1
        generation = self._generation
        self._ended_generation = None
        self._stop_reason = None
        self._stop_requested_generation = None
        self._stream_serial = serial
        self._parser.reset_context()
        self.running.value = True
        self.status.value = "Memulai logcat"

        def on_batch(lines: list[str]) -> None:
            self._dispatcher.post(lambda: self._receive_batch(generation, lines))

        def on_end(returncode: int, message: str | None) -> None:
            self._dispatcher.post(
                lambda: self._finish_stream(generation, returncode, message)
            )

        try:
            handle = self._service.start_stream(serial, on_batch, on_end)
        except AdbError as error:
            self._stream_serial = None
            self.running.value = False
            self.status.value = f"Gagal memulai logcat: {error}"
            return

        if self._ended_generation != generation:
            self._stream_handle = handle
            self.status.value = "Logcat berjalan"
            if self._stop_reason is not None:
                self._schedule_stop(handle, generation)

    def stop(self) -> None:
        self._request_stop("Dihentikan")

    def toggle_pause(self) -> None:
        self.paused.value = not self.paused.value

    def clear_view(self) -> None:
        self._visible.clear()
        self.visible_count.value = 0
        self.reset.emit(None)

    def clear_device_buffer(self) -> None:
        serial = self._selected_serial.value
        if serial is None:
            self.status.value = "Pilih perangkat ADB terlebih dahulu."
            return
        self.status.value = "Menghapus buffer logcat perangkat"
        future = self._executor.submit(self._service.clear_buffer, serial)
        future.add_done_callback(
            lambda completed: self._dispatcher.post(
                lambda: self._finish_clear_buffer(completed)
            )
        )

    def dump_recent(self, count: int) -> None:
        serial = self._selected_serial.value
        if serial is None:
            self.status.value = "Pilih perangkat ADB terlebih dahulu."
            return
        self.status.value = "Mengambil logcat terbaru"
        future = self._executor.submit(self._service.dump, serial, count)
        future.add_done_callback(
            lambda completed: self._dispatcher.post(
                lambda: self._finish_dump(completed)
            )
        )

    def set_min_level(self, level: str) -> None:
        if level not in _LEVEL_ORDER:
            raise ValueError("Level minimum harus salah satu dari V, D, I, W, E, atau F.")
        self.min_level.value = level

    def set_tag_query(self, query: str) -> None:
        self.tag_query.value = query

    def set_text_query(self, query: str) -> None:
        self.text_query.value = query

    def snapshot_visible(self) -> list[LogcatEntry]:
        return list(self._visible)

    def export_visible(self, path: str | Path, overwrite: bool = False) -> bool:
        target = Path(path)
        if not target.is_absolute():
            self.status.value = "Path ekspor harus absolut."
            return False
        if not target.parent.is_dir():
            self.status.value = "Folder tujuan ekspor tidak ditemukan."
            return False
        if target.exists() and not overwrite:
            self.status.value = "Berkas tujuan sudah ada; izinkan timpa untuk melanjutkan."
            return False

        entries = self.snapshot_visible()
        self.status.value = "Mengekspor logcat"
        future = self._executor.submit(self._write_export, target, entries, overwrite)
        future.add_done_callback(
            lambda completed: self._dispatcher.post(
                lambda: self._finish_export(completed, target)
            )
        )
        return True

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        if self._stream_handle is not None:
            self._stream_handle.stop()
            self._stream_handle = None
        self._service.close()
        if self._owns_executor:
            self._executor.shutdown(wait=False, cancel_futures=True)

    def _receive_batch(self, generation: int, lines: list[str]) -> None:
        if generation != self._generation or self._ended_generation == generation:
            return
        parsed = self._parser.parse_lines(lines)
        self._append_entries(parsed)

    def _append_entries(self, entries: list[LogcatEntry]) -> None:
        appended: list[LogcatEntry] = []
        for entry in entries:
            if len(self._entries) == _RING_BUFFER_SIZE:
                removed = self._entries.popleft()
                if (
                    not self.paused.value
                    and self._matches(removed)
                    and self._visible
                    and self._visible[0].seq == removed.seq
                ):
                    self._visible.popleft()
            self._entries.append(entry)
            if not self.paused.value and self._matches(entry):
                self._visible.append(entry)
                appended.append(entry)

        self.total_count.value = len(self._entries)
        if not self.paused.value:
            self.visible_count.value = len(self._visible)
            if appended:
                self.batch_appended.emit(appended)

    def _rebuild_visible(self) -> None:
        query = self.text_query.value.casefold()
        minimum_level = self.min_level.value
        tag_query = self.tag_query.value.casefold()
        self._visible = deque(
            entry
            for entry in self._entries
            if self._matches(entry, minimum_level, tag_query, query)
        )
        self.visible_count.value = len(self._visible)
        self.reset.emit(None)

    def _matches(
        self,
        entry: LogcatEntry,
        minimum_level: str | None = None,
        tag_query: str | None = None,
        text_query: str | None = None,
    ) -> bool:
        minimum_level = self.min_level.value if minimum_level is None else minimum_level
        tag_query = self.tag_query.value.casefold() if tag_query is None else tag_query
        text_query = self.text_query.value.casefold() if text_query is None else text_query
        if entry.level == "M":
            return not text_query
        if _LEVEL_ORDER.index(entry.level) < _LEVEL_ORDER.index(minimum_level):
            return False
        if tag_query and tag_query not in entry.tag.casefold():
            return False
        return not text_query or text_query in (
            entry.tag + " " + entry.message
        ).casefold()

    def _paused_changed(self, paused: bool) -> None:
        if not paused:
            self._rebuild_visible()

    def _selected_serial_changed(self, serial: str | None) -> None:
        if self.running.value and serial != self._stream_serial:
            self._request_stop("Dihentikan: perangkat terpilih berubah")

    def _lifecycle_event(self, action: str) -> None:
        if action == "reboot":
            self._request_stop("Dihentikan: perangkat dimulai ulang")
        elif action == "reset":
            self._request_stop("Dihentikan: Reset ADB")

    def _request_stop(self, reason: str) -> None:
        if not self.running.value:
            return
        self._stop_reason = reason
        self.status.value = reason
        handle = self._stream_handle
        if handle is not None:
            self._schedule_stop(handle, self._generation)

    def _schedule_stop(self, handle: StreamHandle, generation: int) -> None:
        if self._stop_requested_generation == generation:
            return
        self._stop_requested_generation = generation
        future = self._executor.submit(handle.stop)
        future.add_done_callback(
            lambda completed: self._dispatcher.post(
                lambda: self._finish_stop_request(completed)
            )
        )

    def _finish_stop_request(self, future: Future[None]) -> None:
        try:
            future.result()
        except Exception as error:
            self.status.value = f"Gagal menghentikan logcat: {error}"

    def _finish_stream(self, generation: int, returncode: int, message: str | None) -> None:
        if generation != self._generation or self._ended_generation == generation:
            return
        self._ended_generation = generation
        self._stream_handle = None
        self._stream_serial = None
        self.running.value = False
        if self._stop_reason is not None:
            self.status.value = self._stop_reason
        elif message is not None:
            self.status.value = message
        elif returncode == 0:
            self.status.value = "Logcat berhenti."
        else:
            self.status.value = f"Logcat berhenti dengan kode {returncode}."

    def _finish_clear_buffer(self, future: Future[None]) -> None:
        try:
            future.result()
        except Exception as error:
            self.status.value = f"Gagal menghapus buffer logcat: {error}"
        else:
            self.status.value = "Buffer logcat perangkat dibersihkan."

    def _finish_dump(self, future: Future[list[str]]) -> None:
        try:
            lines = future.result()
        except (AdbError, ValueError) as error:
            self.status.value = f"Gagal mengambil logcat: {error}"
            return
        except Exception as error:
            self.status.value = f"Kesalahan saat mengambil logcat: {error}"
            return
        self._append_entries(self._parser.parse_lines(lines))
        self.status.value = "Logcat terbaru dimuat."

    def _finish_export(self, future: Future[None], target: Path) -> None:
        try:
            future.result()
        except OSError as error:
            self.status.value = f"Gagal mengekspor logcat: {error}"
        else:
            self.status.value = f"Logcat diekspor ke {target}."

    @staticmethod
    def _write_export(
        path: Path,
        entries: list[LogcatEntry],
        overwrite: bool,
    ) -> None:
        mode = "w" if overwrite else "x"
        with path.open(mode, encoding="utf-8", newline="\n") as output:
            output.writelines(f"{entry.raw}\n" for entry in entries)
