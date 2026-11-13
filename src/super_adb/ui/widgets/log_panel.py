from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from super_adb.models.log_entry import LogEntry


class LogPanel(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("logPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        heading = QHBoxLayout()
        title = QLabel("Terminal Log", self)
        title.setObjectName("panelTitle")
        heading.addWidget(title)
        heading.addStretch(1)
        self.wrap_toggle = QToolButton(self)
        self.wrap_toggle.setObjectName("logWrapToggle")
        self.wrap_toggle.setText("Wrap")
        self.wrap_toggle.setCheckable(True)
        self.wrap_toggle.setChecked(True)
        self.wrap_toggle.setToolTip("Aktif/nonaktifkan word wrap pada log")
        self.wrap_toggle.toggled.connect(self._set_wrap_enabled)
        heading.addWidget(self.wrap_toggle)
        layout.addLayout(heading)

        self.output = QPlainTextEdit(self)
        self.output.setObjectName("logOutput")
        self.output.setReadOnly(True)
        self.output.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.output.setMaximumBlockCount(2000)
        self.output.setFont(self._monospace_font())
        layout.addWidget(self.output, 1)

    def append_entry(self, entry: LogEntry) -> None:
        self.append_text(entry.text)

    def append_text(self, text: str) -> None:
        self.output.appendPlainText(text)

    def clear(self) -> None:
        self.output.clear()

    def _set_wrap_enabled(self, enabled: bool) -> None:
        mode = (
            QPlainTextEdit.LineWrapMode.WidgetWidth
            if enabled
            else QPlainTextEdit.LineWrapMode.NoWrap
        )
        self.output.setLineWrapMode(mode)

    @staticmethod
    def _monospace_font() -> QFont:
        for family in ("Cascadia Mono", "Consolas"):
            if QFontDatabase.hasFamily(family):
                font = QFont(family, 10)
                font.setStyleHint(QFont.StyleHint.Monospace)
                font.setFixedPitch(True)
                return font
        font = QFont("monospace", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setFixedPitch(True)
        return font
