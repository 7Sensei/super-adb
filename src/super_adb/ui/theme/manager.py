from pathlib import Path
from string import Template

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from super_adb.models.app_settings import ThemeMode
from super_adb.ui.theme.tokens import tokens_for


class ThemeManager(QObject):
    themeChanged = Signal(object)

    def __init__(self, application: QApplication, font_family: str = "Segoe UI") -> None:
        super().__init__(application)
        self._application = application
        self.font_family = font_family
        self.mode: ThemeMode = "dark"
        self.tokens = tokens_for("dark")
        self._template_path = Path(__file__).with_name("template.qss")
        self._template = Template(self._template_path.read_text(encoding="utf-8"))
        self._application.setStyle("Fusion")
        self.apply("dark")

    def apply(self, mode: ThemeMode) -> None:
        if mode not in {"light", "dark", "system"}:
            raise ValueError(f"Mode tema tidak dikenal: {mode!r}")
        self.mode = mode
        resolved = self._resolve_mode(mode)
        self.tokens = tokens_for(resolved)
        values = self.tokens.as_qss()
        values["font_family"] = self.font_family.replace('"', "")
        self._application.setStyleSheet(self._template.substitute(values))
        self.themeChanged.emit(self.tokens)

    def set_font_family(self, family: str) -> None:
        if not family:
            raise ValueError("Nama font tidak boleh kosong.")
        self.font_family = family
        self.apply(self.mode)

    def _resolve_mode(self, mode: ThemeMode) -> ThemeMode:
        if mode != "system":
            return mode
        hints = QGuiApplication.styleHints()
        color_scheme = hints.colorScheme() if hints is not None else Qt.ColorScheme.Unknown
        return "light" if color_scheme == Qt.ColorScheme.Light else "dark"
