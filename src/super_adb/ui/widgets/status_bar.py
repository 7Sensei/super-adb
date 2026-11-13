from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget


class StatusBar(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("statusStrip")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        self.status_label = QLabel("Siap")
        self.status_label.setObjectName("statusMessage")
        layout.addWidget(self.status_label, 1)

        self.busy_label = QLabel("SIAP")
        self.busy_label.setObjectName("busyPill")
        layout.addWidget(self.busy_label)

        self.elapsed_label = QLabel("")
        self.elapsed_label.setObjectName("elapsedTime")
        layout.addWidget(self.elapsed_label)

        separator = QFrame(self)
        separator.setObjectName("statusSeparator")
        separator.setFrameShape(QFrame.Shape.VLine)
        layout.addWidget(separator)

        self.device_count = QLabel("0 perangkat")
        self.device_count.setObjectName("deviceCount")
        layout.addWidget(self.device_count)

    def set_status(self, message: str) -> None:
        self.status_label.setText(message)

    def set_busy(self, busy: bool, elapsed: str = "") -> None:
        self.busy_label.setText("BERJALAN" if busy else "SIAP")
        self.busy_label.setProperty("active", busy)
        self.busy_label.style().unpolish(self.busy_label)
        self.busy_label.style().polish(self.busy_label)
        self.elapsed_label.setText(elapsed if busy else "")

    def set_device_count(self, count: int) -> None:
        self.device_count.setText(f"{count} perangkat")
