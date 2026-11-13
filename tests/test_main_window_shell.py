from concurrent.futures import Executor, Future

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication, QComboBox, QPushButton

from super_adb.models.app_settings import AppSettings
from super_adb.models.device import Device
from super_adb.models.device_info import DeviceInfo
from super_adb.services.errors import AdbNotFoundError
from super_adb.services.settings_store import SettingsStore
from super_adb.ui.main_window import MainWindow
from super_adb.ui.pages import apps as apps_page
from super_adb.ui.pages import network as network_page
from super_adb.ui.theme.manager import ThemeManager
from super_adb.viewmodels.main_viewmodel import MainViewModel
from super_adb.viewmodels.settings_viewmodel import SettingsViewModel


class FakeAdb:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []
        self.closed = False

    def close(self) -> None:
        self.closed = True

    def execute(self, command, on_line):
        self.commands.append(command)
        if command[1:2] == ["devices"]:
            return "List of devices attached\nserial-1\tdevice\n"
        return ""

    def get_device_info(self, serial: str) -> DeviceInfo:
        return DeviceInfo(
            serial=serial,
            state="device",
            brand="Google",
            model="Pixel 8",
            product_name="shiba",
            android_version="14",
            api_level=34,
            chipset="Tensor",
            cpu_abi="arm64-v8a",
            screen_w=1080,
            screen_h=2400,
            density=420,
            ram_gb=8.0,
            battery_level=75,
            charging=True,
        )


class MissingAdb(FakeAdb):
    def execute(self, command, on_line):
        self.commands.append(command)
        raise AdbNotFoundError("ADB tidak ditemukan. Tambahkan Android Platform Tools ke PATH.")


class ImmediateDispatcher:
    def __init__(self) -> None:
        self.closed = False

    def post(self, callback) -> None:
        callback()

    def close(self) -> None:
        self.closed = True


class SyncExecutor(Executor):
    def __init__(self) -> None:
        self.shutdown_calls: list[tuple[bool, bool]] = []

    def submit(self, fn, /, *args, **kwargs):
        future = Future()
        try:
            future.set_result(fn(*args, **kwargs))
        except Exception as error:
            future.set_exception(error)
        return future

    def shutdown(self, wait=True, *, cancel_futures=False) -> None:
        self.shutdown_calls.append((wait, cancel_futures))


class FakeSettingsStore(SettingsStore):
    def __init__(self) -> None:
        self.settings = AppSettings()

    def load(self) -> AppSettings:
        return self.settings

    def save(self, settings: AppSettings) -> None:
        self.settings = settings


def build_window(
    qapp: QApplication,
    window_settings: QSettings | None = None,
) -> MainWindow:
    dispatcher = ImmediateDispatcher()
    viewmodel = MainViewModel(FakeAdb(), dispatcher, SyncExecutor())
    settings_viewmodel = SettingsViewModel(FakeSettingsStore())
    theme_manager = ThemeManager(qapp)
    return MainWindow(
        viewmodel,
        settings_viewmodel,
        theme_manager,
        dispatcher,
        window_settings,
    )


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

    window._log_panel.append_text("clear me")
    qtbot.keyClick(window, Qt.Key.Key_L, modifier=Qt.KeyboardModifier.ControlModifier)
    assert window._log_panel.output.toPlainText() == ""

    commands_before_refresh = len(window._viewmodel._adb_service.commands)
    qtbot.keyClick(window, Qt.Key.Key_F5)
    assert len(window._viewmodel._adb_service.commands) == commands_before_refresh + 1


def test_pages_expose_all_existing_actions_and_settings(qtbot, qapp: QApplication) -> None:
    window = build_window(qapp)
    qtbot.addWidget(window)

    expected_actions = (
        {
            "action-check-devices",
            "action-basic-info",
            "action-hardware",
            "action-battery",
            "action-reboot",
        },
        {"action-install-apk", "action-list-apps", "action-uninstall-app"},
        {"action-enable-tcpip", "action-connect-wireless", "action-disconnect-devices"},
    )
    for index, expected in enumerate(expected_actions):
        page = window.page_stack.widget(index)
        actual = {button.objectName() for button in page.findChildren(QPushButton)}
        assert actual == expected

    settings = window.page_stack.widget(3)
    theme_selector = settings.findChild(QComboBox, "themeSelector")
    assert theme_selector is not None
    theme_selector.setCurrentIndex(theme_selector.findData("light"))
    assert window._settings_viewmodel.theme_mode.value == "light"


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


def test_missing_adb_is_visible_in_status_and_log(qtbot, qapp: QApplication) -> None:
    dispatcher = ImmediateDispatcher()
    viewmodel = MainViewModel(MissingAdb(), dispatcher, SyncExecutor())
    settings_viewmodel = SettingsViewModel(FakeSettingsStore())
    theme_manager = ThemeManager(qapp)
    window = MainWindow(viewmodel, settings_viewmodel, theme_manager, dispatcher)
    qtbot.addWidget(window)

    message = "ADB tidak ditemukan. Tambahkan Android Platform Tools ke PATH."
    assert window._status_bar.status_label.text() == message
    assert f"Error: {message}" in window._log_panel.output.toPlainText()


def test_page_actions_preserve_install_uninstall_and_wireless_flows(
    qtbot,
    qapp: QApplication,
    monkeypatch,
) -> None:
    window = build_window(qapp)
    qtbot.addWidget(window)
    window.show()
    viewmodel = window._viewmodel
    adb = viewmodel._adb_service
    adb.commands.clear()

    monkeypatch.setattr(apps_page, "choose_apk_file", lambda parent: r"C:\temp\sample.apk")
    monkeypatch.setattr(apps_page, "ask_package_name", lambda parent: "com.example.sample")
    window.icon_rail.pageRequested.emit("apps")
    for action_id in ("install-apk", "uninstall-app"):
        button = window.findChild(QPushButton, f"action-{action_id}")
        assert button is not None
        qtbot.mouseClick(button, Qt.MouseButton.LeftButton)

    monkeypatch.setattr(network_page, "ask_device_ip", lambda parent: "192.0.2.1")
    window.icon_rail.pageRequested.emit("network")
    connect_button = window.findChild(QPushButton, "action-connect-wireless")
    assert connect_button is not None
    qtbot.mouseClick(connect_button, Qt.MouseButton.LeftButton)

    assert adb.commands == [
        ["adb", "-s", "serial-1", "install", r"C:\temp\sample.apk"],
        ["adb", "-s", "serial-1", "uninstall", "com.example.sample"],
        ["adb", "connect", "192.0.2.1"],
    ]
    assert "Menjalankan: adb -s serial-1 install C:\\temp\\sample.apk" in (
        window._log_panel.output.toPlainText()
    )


def test_device_panel_shows_available_details_and_connection_state(
    qtbot,
    qapp: QApplication,
) -> None:
    window = build_window(qapp)
    qtbot.addWidget(window)
    qtbot.waitUntil(lambda: window._viewmodel.device_info.value is not None)
    panel = window._device_panel

    assert panel.state_badge.text() == "ONLINE"
    assert panel.device_name.text() == "Pixel 8"
    assert panel._rows["android"].text() == "14"
    assert panel._rows["resolution"].text() == "1080 × 2400"
    assert panel._rows["ram"].text() == "8 GB"
    assert panel.battery_bar.value() == 75
    assert panel.battery_status.text() == "Sedang mengisi daya"
    assert not panel.mockup.grab().isNull()

    window._viewmodel._update_devices([Device("serial-1", "unauthorized")])
    assert panel.state_badge.text() == "UNAUTHORIZED"
    assert panel._rows["brand"].text() == "—"
    assert panel.battery_bar.isHidden()

    window._viewmodel.select_device(None)
    assert panel.state_badge.text() == "TIDAK ADA DEVICE"


def test_closing_window_stops_timers_dispatcher_service_and_executor(
    qtbot,
    qapp: QApplication,
    tmp_path,
) -> None:
    window_settings = QSettings(str(tmp_path / "window.ini"), QSettings.Format.IniFormat)
    window = build_window(qapp, window_settings)
    window.show()
    qtbot.wait(20)
    window.resize(1100, 700)
    qtbot.wait(20)
    qtbot.addWidget(window)

    window.close()

    assert not window._poll_timer.isActive()
    assert not window._device_info_timer.isActive()
    assert not window._elapsed_timer.isActive()
    assert window._viewmodel._adb_service.closed
    assert window._viewmodel._executor.shutdown_calls == [(False, True)]
    assert window._dispatcher.closed
    assert window_settings.value("window/geometry") is not None

    restored = build_window(qapp, window_settings)
    qtbot.addWidget(restored)
    restored.show()
    qtbot.wait(20)
    assert restored.height() == window.height()
