from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future
from pathlib import Path

import pytest

from super_adb.models.device import Device
from super_adb.models.device_info import DeviceInfo
from super_adb.models.logcat_entry import LogcatEntry
from super_adb.viewmodels.base import Observable, Signal
from super_adb.viewmodels.logcat_viewmodel import LogcatViewModel
from super_adb.viewmodels.main_viewmodel import MainViewModel


class ImmediateDispatcher:
    def post(self, callback: Callable[[], None]) -> None:
        callback()


class SyncExecutor:
    def submit(self, fn, /, *args, **kwargs) -> Future:
        future = Future()
        try:
            future.set_result(fn(*args, **kwargs))
        except Exception as error:
            future.set_exception(error)
        return future


class FakeStreamHandle:
    def __init__(self, on_end: Callable[[int, str | None], None]) -> None:
        self.on_end = on_end
        self.active = True
        self.stop_calls = 0

    def stop(self) -> None:
        self.stop_calls += 1
        if self.active:
            self.active = False
            self.on_end(-15, None)


class FakeLogcatService:
    def __init__(self, dump_lines: list[str] | None = None) -> None:
        self.dump_lines = dump_lines or []
        self.serial: str | None = None
        self.on_batch: Callable[[list[str]], None] | None = None
        self.handle: FakeStreamHandle | None = None
        self.dump_calls: list[tuple[str, int]] = []
        self.clear_calls: list[str] = []
        self.closed = False

    def start_stream(self, serial: str, on_batch, on_end) -> FakeStreamHandle:
        self.serial = serial
        self.on_batch = on_batch
        self.handle = FakeStreamHandle(on_end)
        return self.handle

    def dump(self, serial: str, count: int) -> list[str]:
        self.dump_calls.append((serial, count))
        return self.dump_lines

    def clear_buffer(self, serial: str) -> None:
        self.clear_calls.append(serial)

    def close(self) -> None:
        self.closed = True

    def emit(self, lines: list[str]) -> None:
        assert self.on_batch is not None
        self.on_batch(lines)

    def end(self, returncode: int = 0, message: str | None = "stream ended") -> None:
        assert self.handle is not None
        if self.handle.active:
            self.handle.active = False
            self.handle.on_end(returncode, message)


class FakeAdbService:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def execute(self, command: list[str], on_line, timeout: float | None = None) -> str:
        self.commands.append(command)
        output = "List of devices attached\nserial-1\tdevice" if command[1:2] == ["devices"] else ""
        if output:
            for output_line in output.splitlines():
                on_line(output_line)
        return output

    def get_device_info(self, serial: str) -> DeviceInfo:
        return DeviceInfo(serial=serial, state="device")

    def close(self) -> None:
        pass


def make_viewmodel(
    service: FakeLogcatService | None = None,
    selected_serial: Observable[str | None] | None = None,
    lifecycle_events: Signal[str] | None = None,
) -> tuple[LogcatViewModel, FakeLogcatService, Observable[str | None]]:
    selected = selected_serial or Observable("serial-1")
    fake_service = service or FakeLogcatService()
    viewmodel = LogcatViewModel(
        fake_service,
        selected,
        ImmediateDispatcher(),
        lifecycle_events,
        SyncExecutor(),
    )
    return viewmodel, fake_service, selected


def line(level: str, tag: str, message: str, seq: int = 1) -> str:
    return f"06-15 14:32:10.{seq:03} 1 2 {level} {tag}: {message}"


def test_filters_level_tag_text_and_meta_entries() -> None:
    viewmodel, service, _ = make_viewmodel()
    resets: list[None] = []
    appended: list[list[LogcatEntry]] = []
    viewmodel.reset.connect(resets.append)
    viewmodel.batch_appended.connect(appended.append)
    viewmodel.start()
    service.emit(
        [
            "--------- beginning of main",
            line("I", "Net Manager", "Connected"),
            line("D", "Network Tag", "packet sent", 2),
            line("W", "Worker", "slow response", 3),
            line("E", "Worker", "timeout", 4),
            line("F", "Daemon", "crashed", 5),
        ]
    )

    assert viewmodel.total_count.value == 6
    assert len(appended) == 1
    assert len(appended[0]) == 6

    viewmodel.set_min_level("W")
    assert [entry.level for entry in viewmodel.snapshot_visible()] == ["M", "W", "E", "F"]
    viewmodel.set_tag_query("wOrKeR")
    assert [entry.tag for entry in viewmodel.snapshot_visible()] == ["", "Worker", "Worker"]
    viewmodel.set_text_query("TIMEOUT")
    assert [entry.message for entry in viewmodel.snapshot_visible()] == ["timeout"]
    assert viewmodel.visible_count.value == 1
    assert len(resets) == 3


def test_invalid_minimum_level_is_rejected() -> None:
    viewmodel, _, _ = make_viewmodel()

    with pytest.raises(ValueError, match="Level minimum"):
        viewmodel.set_min_level("M")


def test_pausing_keeps_buffer_current_but_freezes_display_until_resume() -> None:
    viewmodel, service, _ = make_viewmodel()
    appended: list[list[LogcatEntry]] = []
    resets: list[None] = []
    viewmodel.batch_appended.connect(appended.append)
    viewmodel.reset.connect(resets.append)
    viewmodel.start()
    service.emit([line("I", "Test", "first")])

    viewmodel.toggle_pause()
    service.emit([line("I", "Test", "second", 2)])

    assert viewmodel.paused.value is True
    assert viewmodel.total_count.value == 2
    assert viewmodel.visible_count.value == 1
    assert [entry.message for entry in viewmodel.snapshot_visible()] == ["first"]
    assert len(appended) == 1

    viewmodel.toggle_pause()

    assert viewmodel.paused.value is False
    assert [entry.message for entry in viewmodel.snapshot_visible()] == ["first", "second"]
    assert viewmodel.visible_count.value == 2
    assert len(resets) == 1


def test_ring_buffer_discards_old_entries_at_capacity() -> None:
    viewmodel, service, _ = make_viewmodel()
    viewmodel.start()
    service.emit(
        [line("I", "Test", f"entry {index}", index % 1000) for index in range(50_001)]
    )

    visible = viewmodel.snapshot_visible()
    assert viewmodel.total_count.value == 50_000
    assert viewmodel.visible_count.value == 50_000
    assert len(visible) == 50_000
    assert visible[0].message == "entry 1"
    assert visible[-1].message == "entry 50000"


@pytest.mark.parametrize(
    ("changed_serial", "event", "expected_status"),
    [
        ("serial-2", None, "Dihentikan: perangkat terpilih berubah"),
        (None, "reboot", "Dihentikan: perangkat dimulai ulang"),
        (None, "reset", "Dihentikan: Reset ADB"),
    ],
)
def test_device_change_reboot_and_reset_stop_the_stream(
    changed_serial: str | None,
    event: str | None,
    expected_status: str,
) -> None:
    lifecycle_events: Signal[str] = Signal()
    viewmodel, service, selected = make_viewmodel(lifecycle_events=lifecycle_events)
    viewmodel.start()

    if event is not None:
        lifecycle_events.emit(event)
    else:
        selected.value = changed_serial

    assert viewmodel.running.value is False
    assert viewmodel.status.value == expected_status
    assert service.handle is not None
    assert service.handle.stop_calls == 1


@pytest.mark.parametrize(
    ("action", "expected_status"),
    [
        ("reboot_device", "Dihentikan: perangkat dimulai ulang"),
        ("reset_adb", "Dihentikan: Reset ADB"),
    ],
)
def test_main_viewmodel_lifecycle_actions_stop_logcat(
    action: str,
    expected_status: str,
) -> None:
    adb = FakeAdbService()
    main_viewmodel = MainViewModel(adb, ImmediateDispatcher(), SyncExecutor())
    main_viewmodel._update_devices([Device("serial-1", "device")])
    logcat_service = FakeLogcatService()
    logcat_viewmodel = LogcatViewModel(
        logcat_service,
        main_viewmodel.selected_serial,
        ImmediateDispatcher(),
        main_viewmodel.lifecycle_event,
        SyncExecutor(),
    )
    logcat_viewmodel.start()

    getattr(main_viewmodel, action)()

    assert logcat_viewmodel.running.value is False
    assert logcat_viewmodel.status.value == expected_status
    assert logcat_service.handle is not None
    assert logcat_service.handle.stop_calls == 1
    if action == "reset_adb":
        assert adb.commands[:2] == [["adb", "kill-server"], ["adb", "start-server"]]
    else:
        assert adb.commands == [["adb", "-s", "serial-1", "reboot"]]


def test_stop_is_independent_of_main_viewmodel_busy_state() -> None:
    viewmodel, service, _ = make_viewmodel()
    viewmodel.start()
    viewmodel.stop()

    assert viewmodel.running.value is False
    assert viewmodel.status.value == "Dihentikan"
    assert service.handle is not None
    assert service.handle.stop_calls == 1


def test_clear_device_buffer_and_dump_recent_use_selected_device() -> None:
    service = FakeLogcatService([line("W", "Test", "from dump")])
    viewmodel, service, _ = make_viewmodel(service)

    viewmodel.clear_device_buffer()
    viewmodel.dump_recent(100)

    assert service.clear_calls == ["serial-1"]
    assert service.dump_calls == [("serial-1", 100)]
    assert viewmodel.snapshot_visible()[0].message == "from dump"
    assert viewmodel.status.value == "Logcat terbaru dimuat."


def test_export_validates_path_and_writes_visible_raw_lines(tmp_path: Path) -> None:
    viewmodel, service, _ = make_viewmodel()
    viewmodel.start()
    raw = line("E", "Test", "export me")
    service.emit([raw])

    assert viewmodel.export_visible("relative.log") is False
    assert viewmodel.export_visible(tmp_path / "missing" / "log.txt") is False

    target = tmp_path / "visible.log"
    assert viewmodel.export_visible(target) is True
    assert target.read_text(encoding="utf-8") == raw + "\n"
    assert viewmodel.status.value == f"Logcat diekspor ke {target}."


def test_export_requires_explicit_overwrite(tmp_path: Path) -> None:
    viewmodel, service, _ = make_viewmodel()
    viewmodel.start()
    service.emit([line("I", "Test", "replacement")])
    target = tmp_path / "existing.txt"
    target.write_text("original\n", encoding="utf-8")

    assert viewmodel.export_visible(target) is False
    assert target.read_text(encoding="utf-8") == "original\n"
    assert viewmodel.export_visible(target, overwrite=True) is True
    assert target.read_text(encoding="utf-8").endswith("replacement\n")


def test_start_without_selected_device_and_filtering_meta_text() -> None:
    selected = Observable(None)
    viewmodel, service, _ = make_viewmodel(selected_serial=selected)
    viewmodel.start()

    assert service.serial is None
    assert viewmodel.status.value == "Pilih perangkat ADB terlebih dahulu."

    viewmodel, service, _ = make_viewmodel()
    viewmodel.start()
    service.emit(["--------- beginning of main"])
    viewmodel.set_text_query("main")

    assert viewmodel.snapshot_visible() == []
