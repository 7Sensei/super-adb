import ctypes
import sys
from collections.abc import Callable

from PySide6.QtCore import QElapsedTimer, QSettings, Qt, QTimer
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut, QShowEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from super_adb.models.app_settings import ThemeMode
from super_adb.models.device import Device
from super_adb.ui.icons import load_icon
from super_adb.ui.pages.apps import AppsPage
from super_adb.ui.pages.network import NetworkPage
from super_adb.ui.pages.settings import SettingsPage
from super_adb.ui.pages.system import SystemPage
from super_adb.ui.qt_dispatcher import QtDispatcher
from super_adb.ui.theme.manager import ThemeManager
from super_adb.ui.theme.tokens import ThemeTokens, tokens_for
from super_adb.ui.widgets.device_chips import DeviceChips
from super_adb.ui.widgets.device_panel import DevicePanel
from super_adb.ui.widgets.icon_rail import IconRail
from super_adb.ui.widgets.log_panel import LogPanel
from super_adb.ui.widgets.status_bar import StatusBar
from super_adb.viewmodels.main_viewmodel import MainViewModel
from super_adb.viewmodels.settings_viewmodel import SettingsViewModel

_PAGE_DETAILS = {
    "system": ("Sistem", "Informasi dan kontrol perangkat Android"),
    "apps": ("Aplikasi", "Kelola aplikasi yang terpasang pada perangkat"),
    "network": ("Jaringan", "Hubungkan perangkat melalui ADB over TCP/IP"),
    "settings": ("Pengaturan", "Preferensi tampilan aplikasi"),
}


class MainWindow(QMainWindow):
    def __init__(
        self,
        viewmodel: MainViewModel,
        settings_viewmodel: SettingsViewModel,
        theme_manager: ThemeManager,
        dispatcher: QtDispatcher,
        window_settings: QSettings | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Super-ADB")
        self._window_settings = window_settings
        self.setMinimumSize(1000, 650)
        self.resize(1400, 850)
        if self._window_settings is not None:
            geometry = self._window_settings.value("window/geometry")
            if geometry:
                self.restoreGeometry(geometry)
        self._viewmodel = viewmodel
        self._settings_viewmodel = settings_viewmodel
        self._theme_manager = theme_manager
        self._dispatcher = dispatcher
        self._unsubscribers: list[Callable[[], None]] = []
        self._is_closing = False
        self._restore_splitter_on_show = True
        self._elapsed = QElapsedTimer()

        self._build_ui()
        self._connect_viewmodels()
        self._log_panel.append_text("Terminal siap...")
        self._log_panel.append_text(f"Font aktif: {self._settings_viewmodel.font_family.value}")
        self._log_panel.append_text("-" * 30)
        self._install_shortcuts()
        self._set_page("system")
        self._apply_theme(self._settings_viewmodel.theme_mode.value)
        self._apply_font(self._settings_viewmodel.font_family.value)

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(3000)
        self._poll_timer.timeout.connect(self._viewmodel.poll_devices)
        self._poll_timer.start()

        self._device_info_timer = QTimer(self)
        self._device_info_timer.setInterval(30_000)
        self._device_info_timer.timeout.connect(self._viewmodel.refresh_device_info)
        self._device_info_timer.start()

        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.setInterval(250)
        self._elapsed_timer.timeout.connect(self._update_elapsed)
        self._elapsed_timer.start()
        self._viewmodel.check_devices()

    @property
    def page_stack(self) -> QStackedWidget:
        return self._page_stack

    @property
    def icon_rail(self) -> IconRail:
        return self._icon_rail

    def _build_ui(self) -> None:
        central = QWidget(self)
        central.setObjectName("mainSurface")
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(14, 14, 14, 12)
        root_layout.setSpacing(12)

        root_layout.addWidget(self._build_top_bar())

        body = QHBoxLayout()
        body.setSpacing(12)
        self._icon_rail = IconRail(self._theme_manager, central)
        body.addWidget(self._icon_rail)

        center = self._build_center_content(central)
        body.addWidget(center, 1)
        self._device_panel = DevicePanel(self._viewmodel, self._theme_manager, central)
        body.addWidget(self._device_panel)
        root_layout.addLayout(body, 1)

        self._status_bar = StatusBar(central)
        root_layout.addWidget(self._status_bar)

    def _build_top_bar(self) -> QFrame:
        top_bar = QFrame(self)
        top_bar.setObjectName("topBar")
        layout = QHBoxLayout(top_bar)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(12)

        title = QLabel("Super-ADB")
        title.setObjectName("appTitle")
        layout.addWidget(title)

        divider = QFrame(top_bar)
        divider.setObjectName("topBarSeparator")
        divider.setFrameShape(QFrame.Shape.VLine)
        layout.addWidget(divider)

        self._device_chips = DeviceChips(
            self._viewmodel.devices,
            self._viewmodel.selected_serial,
            self._viewmodel.select_device,
            top_bar,
        )
        layout.addWidget(self._device_chips)
        layout.addStretch(1)

        self._refresh_button = QToolButton(top_bar)
        self._refresh_button.setObjectName("refreshDevices")
        self._refresh_button.setToolTip("Perbarui daftar perangkat")
        self._refresh_button.setIcon(load_icon("refresh-cw.svg", self._theme_manager.tokens.text))
        self._refresh_button.clicked.connect(self._viewmodel.check_devices)
        layout.addWidget(self._refresh_button)

        self._theme_button = QPushButton("Tema", top_bar)
        self._theme_button.setObjectName("themeToggle")
        self._theme_button.setIcon(load_icon("moon.svg", self._theme_manager.tokens.text))
        self._theme_button.setToolTip("Ganti tema terang atau gelap")
        self._theme_button.clicked.connect(self._toggle_theme)
        layout.addWidget(self._theme_button)
        return top_bar

    def _build_center_content(self, parent: QWidget) -> QWidget:
        center = QWidget(parent)
        layout = QVBoxLayout(center)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        heading = QWidget(center)
        heading_layout = QVBoxLayout(heading)
        heading_layout.setContentsMargins(4, 0, 4, 0)
        heading_layout.setSpacing(3)
        self._page_title = QLabel(heading)
        self._page_title.setObjectName("pageTitle")
        heading_layout.addWidget(self._page_title)
        self._page_description = QLabel(heading)
        self._page_description.setObjectName("pageDescription")
        heading_layout.addWidget(self._page_description)
        layout.addWidget(heading)

        splitter = QSplitter(Qt.Orientation.Vertical, center)
        splitter.setObjectName("contentSplitter")
        splitter.setChildrenCollapsible(False)
        self._page_stack = QStackedWidget(splitter)
        self._page_stack.setObjectName("pageStack")
        self._page_stack.addWidget(SystemPage(self._viewmodel, self._theme_manager))
        self._page_stack.addWidget(AppsPage(self._viewmodel, self._theme_manager))
        self._page_stack.addWidget(NetworkPage(self._viewmodel, self._theme_manager))
        self._settings_page = SettingsPage(self._settings_viewmodel, self._theme_manager)
        self._page_stack.addWidget(self._settings_page)
        self._log_panel = LogPanel(splitter)
        splitter.addWidget(self._page_stack)
        splitter.addWidget(self._log_panel)
        self._content_splitter = splitter
        splitter.setStretchFactor(0, 55)
        splitter.setStretchFactor(1, 45)
        self._initial_splitter_sizes: list[int] | None = None
        if self._window_settings is not None:
            sizes = self._window_settings.value("window/content-splitter-sizes")
            if isinstance(sizes, list) and len(sizes) == 2:
                self._initial_splitter_sizes = [int(size) for size in sizes]
        splitter.setSizes(self._initial_splitter_sizes or [55, 45])
        layout.addWidget(splitter, 1)
        return center

    def _connect_viewmodels(self) -> None:
        self._icon_rail.pageRequested.connect(self._set_page)
        self._theme_manager.themeChanged.connect(self._refresh_top_bar_icons)
        self._theme_manager.themeChanged.connect(self._apply_title_bar_theme)
        self._unsubscribers.extend(
            [
                self._viewmodel.devices.subscribe(self._update_device_count),
                self._viewmodel.status.subscribe(self._status_bar.set_status),
                self._viewmodel.is_busy.subscribe(self._update_busy),
                self._viewmodel.log_line.connect(self._log_panel.append_entry),
                self._settings_viewmodel.theme_mode.subscribe(self._apply_theme),
                self._settings_viewmodel.font_family.subscribe(self._apply_font),
            ]
        )
        self._update_device_count(self._viewmodel.devices.value)
        self._status_bar.set_status(self._viewmodel.status.value)
        self._update_busy(self._viewmodel.is_busy.value)

    def _install_shortcuts(self) -> None:
        pages = ("system", "apps", "network", "settings")
        for index, page in enumerate(pages, start=1):
            shortcut = QShortcut(QKeySequence(f"Ctrl+{index}"), self)
            shortcut.activated.connect(lambda page=page: self._set_page(page))
        refresh = QShortcut(QKeySequence("F5"), self)
        refresh.activated.connect(self._viewmodel.check_devices)
        clear_log = QShortcut(QKeySequence("Ctrl+L"), self)
        clear_log.activated.connect(self._log_panel.clear)

    def _set_page(self, page: str) -> None:
        pages = ("system", "apps", "network", "settings")
        index = pages.index(page)
        self._page_stack.setCurrentIndex(index)
        self._icon_rail.set_current_page(page)
        title, description = _PAGE_DETAILS[page]
        self._page_title.setText(title)
        self._page_description.setText(description)

    def _toggle_theme(self) -> None:
        mode: ThemeMode = (
            "dark"
            if self._theme_manager.tokens == tokens_for("light")
            else "light"
        )
        self._settings_viewmodel.set_theme_mode(mode)

    def _apply_theme(self, mode: ThemeMode) -> None:
        self._theme_manager.apply(mode)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._apply_title_bar_theme(self._theme_manager.tokens)
        if self._restore_splitter_on_show:
            self._restore_splitter_on_show = False
            QTimer.singleShot(0, self._restore_initial_splitter_sizes)

    def _restore_initial_splitter_sizes(self) -> None:
        if self._initial_splitter_sizes is not None:
            self._content_splitter.setSizes(self._initial_splitter_sizes)
            return
        height = self._content_splitter.height()
        action_height = round(height * 0.55)
        self._content_splitter.setSizes([action_height, height - action_height])

    def _apply_title_bar_theme(self, tokens: ThemeTokens) -> None:
        if sys.platform != "win32":
            return
        dark_mode = ctypes.c_int(tokens == tokens_for("dark"))
        for attribute in (20, 19):
            try:
                result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    ctypes.c_void_p(int(self.winId())),
                    attribute,
                    ctypes.byref(dark_mode),
                    ctypes.sizeof(dark_mode),
                )
            except (AttributeError, OSError, ctypes.ArgumentError):
                continue
            if result == 0:
                break

    def _apply_font(self, family: str) -> None:
        self._theme_manager.set_font_family(family)

    def _refresh_top_bar_icons(self, tokens: ThemeTokens) -> None:
        is_dark = tokens == tokens_for("dark")
        icon = "sun.svg" if is_dark else "moon.svg"
        color = tokens.text
        self._theme_button.setIcon(load_icon(icon, color))
        self._refresh_button.setIcon(load_icon("refresh-cw.svg", color))

    def _update_device_count(self, devices: list[Device]) -> None:
        self._status_bar.set_device_count(len(devices))

    def _update_busy(self, busy: bool) -> None:
        if busy:
            self._elapsed.start()
        self._status_bar.set_busy(busy)

    def _update_elapsed(self) -> None:
        if self._viewmodel.is_busy.value and self._elapsed.isValid():
            seconds = self._elapsed.elapsed() // 1000
            self._status_bar.set_busy(True, f"{seconds // 60:02}:{seconds % 60:02}")

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._is_closing:
            event.accept()
            return
        self._is_closing = True
        if self._window_settings is not None:
            self._window_settings.setValue("window/geometry", self.saveGeometry())
            self._window_settings.setValue(
                "window/content-splitter-sizes",
                self._content_splitter.sizes(),
            )
            self._window_settings.sync()
        self._poll_timer.stop()
        self._device_info_timer.stop()
        self._elapsed_timer.stop()
        self._device_chips.dispose()
        self._device_panel.dispose()
        self._settings_page.dispose()
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()
        try:
            self._viewmodel.close()
        finally:
            self._dispatcher.close()
            event.accept()
