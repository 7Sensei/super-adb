from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from unittest.mock import Mock, patch

import pytest

from super_adb.models.device import Device
from super_adb.services.errors import AdbNotFoundError
from super_adb.viewmodels.base import Observable, Signal
from super_adb.viewmodels.main_viewmodel import MainViewModel


class FakeAdb:
    def __init__(self, output: str = "", error: Exception | None = None) -> None:
        self.output = output
        self.error = error
        self.commands: list[list[str]] = []

    def execute(self, command: list[str], on_line: Callable[[str], None]) -> str:
        self.commands.append(command)
        if self.error is not None:
            raise self.error
        for line in self.output.splitlines():
            on_line(line)
        return self.output


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
    lines: list[str] = []
    viewmodel.log.connect(lines.append)

    viewmodel.show_battery_status()

    assert viewmodel.status.value == "ADB tidak ditemukan."
    assert "Error: ADB tidak ditemukan." in lines
    assert viewmodel.is_busy.value is False


def test_existing_actions_dispatch_their_original_adb_commands() -> None:
    service = FakeAdb()
    viewmodel = make_viewmodel(service)
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

    assert [command[:2] for command in service.commands] == [
        ["adb", "devices"],
        ["adb", "shell"],
        ["adb", "shell"],
        ["adb", "shell"],
        ["adb", "reboot"],
        ["adb", "shell"],
        ["adb", "install"],
        ["adb", "uninstall"],
        ["adb", "tcpip"],
        ["adb", "connect"],
        ["adb", "disconnect"],
    ]
    assert service.commands[6] == ["adb", "install", "app.apk"]
    assert service.commands[7] == ["adb", "uninstall", "com.example.app"]
    assert service.commands[9] == ["adb", "connect", "192.168.1.2"]
    assert service.commands[2][2].startswith("echo '=== PLATFORM & OS ===';")
    assert "cat /proc/meminfo" in service.commands[2][2]


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
    with patch("super_adb.viewmodels.main_viewmodel.ThreadPoolExecutor", return_value=executor):
        viewmodel = MainViewModel(FakeAdb(), ImmediateDispatcher())

    viewmodel.close()

    executor.shutdown.assert_called_once_with(wait=False, cancel_futures=True)


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
    assert lines == [f"Error: {label} tidak boleh diawali dengan '-'."]
