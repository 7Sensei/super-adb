from collections.abc import Callable

from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QWidget

from super_adb.models.device import Device
from super_adb.viewmodels.base import Observable


class DeviceChips(QWidget):
    def __init__(
        self,
        devices: Observable[list[Device]],
        selected_serial: Observable[str | None],
        select_device: Callable[[str | None], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("deviceChips")
        self._devices = devices
        self._selected_serial = selected_serial
        self._select_device = select_device

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        label = QLabel("ADB")
        label.setObjectName("deviceChipLabel")
        layout.addWidget(label)

        self.selector = QComboBox(self)
        self.selector.setObjectName("deviceSelector")
        self.selector.setMinimumWidth(230)
        self.selector.activated.connect(self._selection_changed)
        layout.addWidget(self.selector)

        self._unsubscribers = [
            self._devices.subscribe(self.refresh_devices),
            self._selected_serial.subscribe(self.select_serial),
        ]
        self.refresh_devices(self._devices.value)
        self.select_serial(self._selected_serial.value)

    def dispose(self) -> None:
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()

    def refresh_devices(self, devices: list[Device]) -> None:
        blocker = QSignalBlocker(self.selector)
        self.selector.clear()
        if not devices:
            self.selector.addItem("Tidak ada perangkat", None)
            self.selector.setEnabled(False)
        else:
            self.selector.setEnabled(True)
            for device in devices:
                status = "Siap" if device.state == "device" else device.state
                self.selector.addItem(f"{device.serial}  ·  {status}", device.serial)
        del blocker
        self.select_serial(self._selected_serial.value)

    def select_serial(self, serial: str | None) -> None:
        if serial is None:
            self.selector.setCurrentIndex(0)
            return
        index = self.selector.findData(serial)
        if index >= 0:
            self.selector.setCurrentIndex(index)

    def _selection_changed(self, index: int) -> None:
        serial = self.selector.itemData(index)
        self._select_device(serial if isinstance(serial, str) else None)
