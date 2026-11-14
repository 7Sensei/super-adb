from pathlib import Path
from string import Template

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QColor, QFontDatabase, QGuiApplication, QPalette
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
        hints = QGuiApplication.styleHints()
        if hasattr(hints, "colorSchemeChanged"):
            hints.colorSchemeChanged.connect(self._system_theme_changed)

    def apply(self, mode: ThemeMode) -> None:
        if mode not in {"light", "dark", "system"}:
            raise ValueError(f"Mode tema tidak dikenal: {mode!r}")
        self.mode = mode
        resolved = self._resolve_mode(mode)
        self.tokens = tokens_for(resolved)
        self._set_color_scheme(mode)
        self._set_palette()
        self._apply_stylesheet()
        self.themeChanged.emit(self.tokens)

    def set_font_family(self, family: str) -> None:
        if not QFontDatabase.hasFamily(family):
            raise ValueError(f"Keluarga font tidak tersedia: {family!r}.")
        previous_family = self.font_family
        self.font_family = family
        try:
            self.apply(self.mode)
        except Exception:
            self.font_family = previous_family
            raise

    def _apply_stylesheet(self) -> None:
        font_family = self.font_family.replace("\\", "\\\\").replace('"', '\\"')
        variables = {**self.tokens.as_qss(), "font_family": font_family}
        self._application.setStyleSheet(self._template.substitute(variables))

    def _resolve_mode(self, mode: ThemeMode) -> ThemeMode:
        if mode != "system":
            return mode
        hints = QGuiApplication.styleHints()
        color_scheme = hints.colorScheme() if hints is not None else Qt.ColorScheme.Unknown
        return "light" if color_scheme == Qt.ColorScheme.Light else "dark"

    def _set_color_scheme(self, mode: ThemeMode) -> None:
        hints = QGuiApplication.styleHints()
        set_color_scheme = getattr(hints, "setColorScheme", None)
        if set_color_scheme is None:
            return
        if mode == "system":
            set_color_scheme(Qt.ColorScheme.Unknown)
        else:
            set_color_scheme(
                Qt.ColorScheme.Light if mode == "light" else Qt.ColorScheme.Dark
            )

    def _set_palette(self) -> None:
        tokens = self.tokens
        palette = QPalette(self._application.palette())
        colors = {
            QPalette.ColorRole.Window: tokens.bg,
            QPalette.ColorRole.WindowText: tokens.text,
            QPalette.ColorRole.Base: tokens.surface,
            QPalette.ColorRole.AlternateBase: tokens.raised,
            QPalette.ColorRole.Text: tokens.text,
            QPalette.ColorRole.Button: tokens.raised,
            QPalette.ColorRole.ButtonText: tokens.text,
            QPalette.ColorRole.Highlight: tokens.accent,
            QPalette.ColorRole.HighlightedText: tokens.accent_text,
            QPalette.ColorRole.ToolTipBase: tokens.raised,
            QPalette.ColorRole.ToolTipText: tokens.text,
        }
        placeholder_role = getattr(QPalette.ColorRole, "PlaceholderText", None)
        if placeholder_role is not None:
            colors[placeholder_role] = tokens.muted
        for group in (
            QPalette.ColorGroup.Active,
            QPalette.ColorGroup.Inactive,
            QPalette.ColorGroup.Disabled,
        ):
            for role, color in colors.items():
                palette.setColor(group, role, QColor(color))
            if group == QPalette.ColorGroup.Disabled:
                for role in (
                    QPalette.ColorRole.WindowText,
                    QPalette.ColorRole.Text,
                    QPalette.ColorRole.ButtonText,
                ):
                    palette.setColor(group, role, QColor(tokens.muted))
                if placeholder_role is not None:
                    palette.setColor(group, placeholder_role, QColor(tokens.muted))
        self._application.setPalette(palette)

    def _system_theme_changed(self, color_scheme: Qt.ColorScheme) -> None:
        if self.mode == "system":
            resolved: ThemeMode = (
                "light" if color_scheme == Qt.ColorScheme.Light else "dark"
            )
            self.tokens = tokens_for(resolved)
            self._set_palette()
            self._apply_stylesheet()
            self.themeChanged.emit(self.tokens)
