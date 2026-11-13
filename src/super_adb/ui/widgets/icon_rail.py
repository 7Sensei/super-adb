from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QToolButton, QVBoxLayout, QWidget

from super_adb.ui.icons import load_icon
from super_adb.ui.theme.manager import ThemeManager
from super_adb.ui.theme.tokens import ThemeTokens


class IconRail(QWidget):
    pageRequested = Signal(str)

    _PAGES = (
        ("system", "monitor.svg", "Sistem"),
        ("apps", "app-window.svg", "Aplikasi"),
        ("network", "wifi.svg", "Jaringan"),
    )

    def __init__(self, theme_manager: ThemeManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("iconRail")
        self.setFixedWidth(68)
        self._theme_manager = theme_manager
        self._buttons: dict[str, QToolButton] = {}
        self._icon_names: dict[str, str] = {}
        self._current_page = "system"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(8)

        brand = QToolButton(self)
        brand.setObjectName("brandMark")
        brand.setText("SA")
        brand.setToolTip("Super-ADB")
        brand.setEnabled(False)
        layout.addWidget(brand)
        self._add_separator(layout)

        for page, icon_name, tooltip in self._PAGES:
            button = self._add_page_button(layout, page, icon_name, tooltip)
            self._buttons[page] = button

        layout.addStretch(1)
        self._add_separator(layout)
        settings_button = self._add_page_button(
            layout,
            "settings",
            "settings.svg",
            "Pengaturan",
        )
        self._buttons["settings"] = settings_button
        theme_manager.themeChanged.connect(self._refresh_icons)
        self._refresh_icons(theme_manager.tokens)
        self.set_current_page(self._current_page)

    @property
    def current_page(self) -> str:
        return self._current_page

    def set_current_page(self, page: str) -> None:
        if page not in self._buttons:
            raise ValueError(f"Halaman tidak dikenal: {page!r}")
        self._current_page = page
        for name, button in self._buttons.items():
            active = name == page
            button.setProperty("active", active)
            button.style().unpolish(button)
            button.style().polish(button)
        self._refresh_icons(self._theme_manager.tokens)

    def _add_page_button(
        self,
        layout: QVBoxLayout,
        page: str,
        icon_name: str,
        tooltip: str,
    ) -> QToolButton:
        button = QToolButton(self)
        button.setObjectName(f"rail-{page}")
        button.setToolTip(tooltip)
        button.setAccessibleName(tooltip)
        button.setFixedSize(48, 48)
        button.clicked.connect(lambda: self.pageRequested.emit(page))
        layout.addWidget(button)
        self._icon_names[page] = icon_name
        return button

    def _refresh_icons(self, tokens: ThemeTokens) -> None:
        for page, button in self._buttons.items():
            color = tokens.accent_text if page == self._current_page else tokens.muted
            button.setIcon(load_icon(self._icon_names[page], color))
            button.setProperty("active", page == self._current_page)
        self.update()

    @staticmethod
    def _add_separator(layout: QVBoxLayout) -> None:
        separator = QFrame()
        separator.setObjectName("railSeparator")
        separator.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(separator)
