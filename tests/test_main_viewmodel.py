from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from unittest.mock import Mock, patch

import pytest

from super_adb.models.device import Device
from super_adb.models.device_info import DeviceInfo
from super_adb.services.errors import AdbNotFoundError
from super_adb.viewmodels.base import Observable, Signal
from super_adb.viewmodels.main_viewmodel import MainViewModel


class FakeAdb:
    def __init__(
        self,
        output: str = "",
        error: Exception | None = None,
        device_info: DeviceInfo | None = None,
    ) -> None:
        self.output = output
        self.error = error
        self.commands: list[list[str]] = []
        self.closed = False

        self.info = device_info or DeviceInfo(serial="serial-1", state="device")

    def close(self) -> None:
        self.closed = True

    def execute(
        self,
        command: list[str],
        on_line: Callable[[str], None],
        timeout: float | None = None,
    ) -> str:
        self.commands.append(command)
        if self.error is not None:
            raise self.error
        for line in self.output.splitlines():
            on_line(line)
        return self.output

    def get_device_info(self, serial: str) -> DeviceInfo:
        return DeviceInfo(
            serial=serial,
            state=self.info.state,
            brand=self.info.brand,
            model=self.info.model,
            product_name=self.info.product_name,
            android_version=self.info.android_version,
            api_level=self.info.api_level,
            chipset=self.info.chipset,
            cpu_abi=self.info.cpu_abi,
            screen_w=self.info.screen_w,
            screen_h=self.info.screen_h,
            density=self.info.density,
            ram_gb=self.info.ram_gb,
            battery_level=self.info.battery_level,
            charging=self.info.charging,
        )


class ImmediateDispatcher:
    def post(self, callback: Callable[[], None]) -> None:
        callback()


class SyncExecutor(ThreadPoolExecutor):
    def __init__(self) -> None:
        super().__init__(max_workers=1)

    def submit(self, fn, /, *args, **kwargs) -> Future:
        future = Future()
        try:
            future.set_result(fn(*args, **kwargs))
        except Exception as error:
            future.set_exception(error)
        return future


class QueuedExecutor:
    def __init__(self) -> None:
        self.tasks: list[tuple[Future, Callable, tuple, dict]] = []

    def submit(self, fn: Callable, /, *args, **kwargs) -> Future:
        future = Future()
        self.tasks.append((future, fn, args, kwargs))
        return future

    def run_next(self) -> None:
        future, fn, args, kwargs = self.tasks.pop(0)
        try:
            future.set_result(fn(*args, **kwargs))
        except Exception as error:
            future.set_exception(error)

    def run_all(self) -> None:
        while self.tasks:
            self.run_next()


def make_viewmodel(service: FakeAdb) -> MainViewModel:
    return MainViewModel(service, ImmediateDispatcher(), SyncExecutor())


def test_check_devices_updates_device_state_and_streams_log() -> None:
    service = FakeAdb(
        "List of devices attached\nserial-1\tdevice\nserial-2\toffline\nserial-3\tunauthorized"
    )
    viewmodel = make_viewmodel(service)
    lines: list[str] = []
    viewmodel.log.connect(lines.append)

    viewmodel.check_devices()

    assert service.commands == [["adb", "devices"]]
    assert viewmodel.devices.value == [
        Device("serial-1", "device"),
        Device("serial-2", "offline"),
        Device("serial-3", "unauthorized"),
    ]
    assert "serial-2\toffline" in lines
    assert viewmodel.is_busy.value is False
    assert viewmodel.status.value == "Selesai"


def test_missing_adb_is_reported_in_state_and_log() -> None:
    viewmodel = make_viewmodel(FakeAdb(error=AdbNotFoundError("ADB tidak ditemukan.")))
    viewmodel._update_devices([Device("serial-1", "device")])
    viewmodel.select_device("serial-1")
    lines: list[str] = []
    viewmodel.log.connect(lines.append)

    viewmodel.show_battery_status()

    assert viewmodel.status.value == "ADB tidak ditemukan."
    assert "Error: ADB tidak ditemukan." in lines
    assert viewmodel.is_busy.value is False


def test_existing_actions_dispatch_their_original_adb_commands() -> None:
    service = FakeAdb(output="serial-1\tdevice")
    viewmodel = make_viewmodel(service)
    viewmodel.check_devices()
    service.commands.clear()
    actions = [
        viewmodel.check_devices,
        viewmodel.show_basic_info,
        viewmodel.check_hardware,
        viewmodel.show_battery_status,
        viewmodel.reboot_device,
        viewmodel.list_apps,
        lambda: viewmodel.install_apk("app.apk"),
        lambda: viewmodel.uninstall_app("com.example.app"),
        viewmodel.enable_tcpip,
        lambda: viewmodel.connect_wireless("192.168.1.2"),
        viewmodel.disconnect_devices,
    ]

    for action in actions:
        action()

    assert [command[:3] for command in service.commands] == [
        ["adb", "devices"],
        ["adb", "-s", "serial-1"],
        ["adb", "-s", "serial-1"],
        ["adb", "-s", "serial-1"],
        ["adb", "-s", "serial-1"],
        ["adb", "-s", "serial-1"],
        ["adb", "-s", "serial-1"],
        ["adb", "-s", "serial-1"],
        ["adb", "-s", "serial-1"],
        ["adb", "connect", "192.168.1.2"],
        ["adb", "disconnect"],
    ]
    assert [command[:2] for command in service.commands] == [
        ["adb", "devices"],
        ["adb", "-s"],
        ["adb", "-s"],
        ["adb", "-s"],
        ["adb", "-s"],
        ["adb", "-s"],
        ["adb", "-s"],
        ["adb", "-s"],
        ["adb", "-s"],
        ["adb", "connect"],
        ["adb", "disconnect"],
    ]
    assert service.commands[6] == ["adb", "-s", "serial-1", "install", "app.apk"]
    assert service.commands[7] == [
        "adb",
        "-s",
        "serial-1",
        "uninstall",
        "com.example.app",
    ]
    assert service.commands[9] == ["adb", "connect", "192.168.1.2"]
    assert service.commands[2][4].startswith("echo '=== PLATFORM & OS ===';")
    assert "cat /proc/meminfo" in service.commands[2][4]


def test_observable_notifies_only_when_value_changes_and_unsubscribes() -> None:
    observable = Observable(1)
    observed: list[int] = []
    unsubscribe = observable.subscribe(observed.append)

    observable.value = 1
    observable.value = 2
    unsubscribe()
    observable.value = 3

    assert observed == [2]


def test_signal_emits_event_without_state() -> None:
    signal: Signal[str] = Signal()
    observed: list[str] = []
    signal.connect(observed.append)

    signal.emit("new log line")

    assert observed == ["new log line"]


def test_close_shuts_down_owned_executor_without_waiting() -> None:
    executor = Mock()
    service = FakeAdb()
    with patch("super_adb.viewmodels.main_viewmodel.ThreadPoolExecutor", return_value=executor):
        viewmodel = MainViewModel(service, ImmediateDispatcher())

    viewmodel.close()

    executor.shutdown.assert_called_once_with(wait=False, cancel_futures=True)
    assert service.closed


@pytest.mark.parametrize(
    ("method_name", "argument", "label"),
    [
        ("install_apk", "-payload.apk", "Path APK"),
        ("uninstall_app", "-k", "Package name"),
        ("connect_wireless", "-192.0.2.1", "IP"),
    ],
)
def test_rejects_dialog_arguments_that_start_with_a_dash(
    method_name: str, argument: str, label: str
) -> None:
    service = FakeAdb()
    viewmodel = make_viewmodel(service)
    lines: list[str] = []
    viewmodel.log.connect(lines.append)

    getattr(viewmodel, method_name)(argument)

    assert service.commands == []
    assert viewmodel.status.value == f"{label} tidak boleh diawali dengan '-'."
    assert lines == [f"{label} tidak boleh diawali dengan '-'."]


def test_auto_selects_one_online_device_and_updates_command_availability() -> None:
    viewmodel = make_viewmodel(FakeAdb())

    viewmodel._update_devices([Device("online-1", "device"), Device("offline-1", "offline")])

    assert viewmodel.selected_serial.value == "online-1"
    assert viewmodel.can_run_device_commands.value is True
    viewmodel.select_device("offline-1")
    assert viewmodel.selected_serial.value == "offline-1"
    assert viewmodel.can_run_device_commands.value is False


def test_poll_devices_is_silent_and_does_not_overlap() -> None:
    service = FakeAdb(output="serial-1\tdevice")
    executor = QueuedExecutor()
    viewmodel = MainViewModel(service, ImmediateDispatcher(), executor)
    logs: list[object] = []
    changes: list[list[Device]] = []
    viewmodel.log_line.connect(logs.append)
    viewmodel.devices.subscribe(changes.append)

    viewmodel.poll_devices()
    viewmodel.poll_devices()

    assert len(executor.tasks) == 1
    assert viewmodel.is_busy.value is False
    assert viewmodel.status.value == "Siap"
    assert logs == []
    executor.run_all()
    assert len(changes) == 1
    assert viewmodel.selected_serial.value == "serial-1"

    viewmodel.poll_devices()
    executor.run_all()
    assert len(changes) == 1
    assert logs == []


def test_log_line_emits_typed_log_entries() -> None:
    service = FakeAdb(output="serial-1\tdevice")
    viewmodel = make_viewmodel(service)
    entries = []
    viewmodel.log_line.connect(entries.append)

    viewmodel.check_devices()

    assert any(entry.kind == "command" for entry in entries)
    assert any(entry.kind == "output" for entry in entries)
    assert all(entry.kind in {"command", "output", "error", "info"} for entry in entries)
