from concurrent.futures import Executor, Future

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from super_adb.models.app_settings import AppSettings
from super_adb.models.device import Device
from super_adb.models.device_info import DeviceInfo
from super_adb.services.settings_store import SettingsStore
from super_adb.ui.main_window import MainWindow
from super_adb.ui.theme.manager import ThemeManager
from super_adb.viewmodels.main_viewmodel import MainViewModel
from super_adb.viewmodels.settings_viewmodel import SettingsViewModel


class FakeAdb:
    def execute(self, command, on_line):
        if command[1:2] == ["devices"]:
            return "List of devices attached\nserial-1\tdevice\n"
        return ""

    def get_device_info(self, serial: str) -> DeviceInfo:
        return DeviceInfo(serial=serial, state="device")


class ImmediateDispatcher:
    def post(self, callback) -> None:
        callback()


class SyncExecutor(Executor):
    def submit(self, fn, /, *args, **kwargs):
        future = Future()
        try:
            future.set_result(fn(*args, **kwargs))
        except Exception as error:
            future.set_exception(error)
        return future

    def shutdown(self, wait=True, *, cancel_futures=False) -> None:
        return


class FakeSettingsStore(SettingsStore):
    def __init__(self) -> None:
        self.settings = AppSettings()

    def load(self) -> AppSettings:
        return self.settings

    def save(self, settings: AppSettings) -> None:
        self.settings = settings


def build_window(qapp: QApplication) -> MainWindow:
    viewmodel = MainViewModel(FakeAdb(), ImmediateDispatcher(), SyncExecutor())
    settings_viewmodel = SettingsViewModel(FakeSettingsStore())
    theme_manager = ThemeManager(qapp)
    return MainWindow(viewmodel, settings_viewmodel, theme_manager)


def test_main_window_builds_shell_and_navigation(qtbot, qapp: QApplication) -> None:
    window = build_window(qapp)
    qtbot.addWidget(window)
    window.show()

    assert window.minimumWidth() == 1000
    assert window.minimumHeight() == 650
    assert window.page_stack.count() == 4
    assert window.page_stack.currentIndex() == 0

    window.activateWindow()
    window.setFocus()
    qtbot.wait(50)
    qtbot.keyClick(window, Qt.Key.Key_2, modifier=Qt.KeyboardModifier.ControlModifier)
    assert window.page_stack.currentIndex() == 1
    assert window.icon_rail.current_page == "apps"


def test_main_window_polls_and_displays_devices(qtbot, qapp: QApplication) -> None:
    window = build_window(qapp)
    qtbot.addWidget(window)

    assert window._poll_timer.interval() == 3000
    assert window._device_info_timer.interval() == 30_000
    assert window._elapsed_timer.interval() == 250

    window._viewmodel.devices.value = [Device(serial="serial-1", state="device")]
    assert window._device_chips.selector.count() == 1
    assert window._status_bar.device_count.text() == "1 perangkat"

    window._device_chips.selector.activated.emit(0)
    assert window._viewmodel.selected_serial.value == "serial-1"

    qtbot.mouseClick(window._theme_button, Qt.MouseButton.LeftButton)
    assert window._settings_viewmodel.theme_mode.value == "light"
