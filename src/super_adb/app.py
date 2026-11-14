import sys

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from super_adb.services.adb_service import SubprocessAdbService
from super_adb.services.logcat_service import SubprocessLogcatService
from super_adb.services.settings_store import JsonSettingsStore
from super_adb.ui.main_window import MainWindow
from super_adb.ui.qt_dispatcher import QtDispatcher
from super_adb.ui.theme.manager import ThemeManager
from super_adb.viewmodels.logcat_viewmodel import LogcatViewModel
from super_adb.viewmodels.main_viewmodel import MainViewModel
from super_adb.viewmodels.settings_viewmodel import SettingsViewModel


def main() -> int:
    application = QApplication(sys.argv)
    application.setOrganizationName("7Sensei")
    application.setApplicationName("Super-ADB")
    application.setApplicationVersion("2.5.0")

    dispatcher = QtDispatcher()
    adb_service = SubprocessAdbService()
    viewmodel = MainViewModel(adb_service, dispatcher)
    logcat_viewmodel = LogcatViewModel(
        SubprocessLogcatService(),
        viewmodel.selected_serial,
        dispatcher,
        viewmodel.lifecycle_event,
    )
    application.aboutToQuit.connect(logcat_viewmodel.close)
    settings_viewmodel = SettingsViewModel(JsonSettingsStore())
    theme_manager = ThemeManager(application, settings_viewmodel.font_family.value)
    window_settings = QSettings()
    window = MainWindow(
        viewmodel,
        settings_viewmodel,
        theme_manager,
        dispatcher,
        window_settings,
    )
    window.show()
    return application.exec()
