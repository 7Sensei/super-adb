from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QLabel, QPlainTextEdit, QVBoxLayout, QWidget

from super_adb.models.log_entry import LogEntry


class LogPanel(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("logPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        title = QLabel("Terminal Log", self)
        title.setObjectName("panelTitle")
        layout.addWidget(title)

        self.output = QPlainTextEdit(self)
        self.output.setObjectName("logOutput")
        self.output.setReadOnly(True)
        self.output.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.output.setMaximumBlockCount(2000)
        self.output.setFont(QFont("Consolas", 10))
        layout.addWidget(self.output, 1)

    def append_entry(self, entry: LogEntry) -> None:
        self.append_text(entry.text)

    def append_text(self, text: str) -> None:
        self.output.appendPlainText(text)

    def clear(self) -> None:
        self.output.clear()
