from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from super_adb.models.device_info import DeviceInfo
from super_adb.ui.theme.manager import ThemeManager
from super_adb.ui.widgets.device_mockup import DeviceMockup
from super_adb.viewmodels.main_viewmodel import MainViewModel


class DevicePanel(QFrame):
    def __init__(
        self,
        viewmodel: MainViewModel,
        theme_manager: ThemeManager,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("devicePanel")
        self.setFixedWidth(320)
        self._viewmodel = viewmodel
        self._unsubscribers = [
            viewmodel.devices.subscribe(self._refresh),
            viewmodel.selected_serial.subscribe(self._refresh),
            viewmodel.device_info.subscribe(self._refresh),
        ]

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(self)
        scroll.setObjectName("devicePanelScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll_area = scroll
        scroll.viewport().setObjectName("devicePanelViewport")
        content = QWidget(scroll)
        content.setObjectName("devicePanelContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        title = QLabel("Perangkat", content)
        title.setObjectName("panelTitle")
        layout.addWidget(title)

        self.state_badge = QLabel("TIDAK ADA DEVICE", content)
        self.state_badge.setObjectName("deviceState")
        self.state_badge.setProperty("status", "none")
        layout.addWidget(self.state_badge)

        self.mockup = DeviceMockup(theme_manager, content)
        layout.addWidget(self.mockup, 1)

        self.device_name = QLabel("Perangkat", content)
        self.device_name.setObjectName("deviceName")
        self.device_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.device_name)
        self.serial_label = QLabel("Pilih perangkat untuk melihat detailnya.", content)
        self.serial_label.setObjectName("deviceSerial")
        self.serial_label.setWordWrap(True)
        layout.addWidget(self.serial_label)

        separator = QFrame(content)
        separator.setObjectName("devicePanelSeparator")
        separator.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(separator)

        self._rows: dict[str, QLabel] = {}
        for key, label in (
            ("brand", "Merek"),
            ("model", "Model"),
            ("product", "Produk"),
            ("android", "Android"),
            ("api", "API Level"),
            ("chipset", "Chipset"),
            ("abi", "CPU ABI"),
            ("resolution", "Resolusi"),
            ("density", "Density"),
            ("ram", "RAM"),
        ):
            self._rows[key] = self._add_detail_row(layout, label, content)

        self.battery_bar = QProgressBar(content)
        self.battery_bar.setObjectName("batteryBar")
        self.battery_bar.setRange(0, 100)
        self.battery_bar.setFormat("Baterai %p%")
        self.battery_bar.setVisible(False)
        layout.addWidget(self.battery_bar)
        self.battery_status = QLabel("", content)
        self.battery_status.setObjectName("mutedText")
        self.battery_status.setVisible(False)
        layout.addWidget(self.battery_status)
        scroll.setWidget(content)
        outer_layout.addWidget(scroll)
        self._refresh(None)

    def dispose(self) -> None:
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()

    def _add_detail_row(self, layout: QVBoxLayout, title: str, parent: QWidget) -> QLabel:
        row = QWidget(parent)
        row.setObjectName("deviceDetailRow")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)
        label = QLabel(title, row)
        label.setObjectName("detailLabel")
        row_layout.addWidget(label, 1)
        value = QLabel("—", row)
        value.setObjectName("detailValue")
        value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        row_layout.addWidget(value)
        layout.addWidget(row)
        return value

    def _refresh(self, value: object) -> None:
        serial = self._viewmodel.selected_serial.value
        device = next(
            (item for item in self._viewmodel.devices.value if item.serial == serial),
            None,
        )
        state = device.state if device is not None else "none"
        info = self._viewmodel.device_info.value
        if info is not None and (info.serial != serial or state != "device"):
            info = None

        status_text = {
            "device": "ONLINE",
            "offline": "OFFLINE",
            "unauthorized": "UNAUTHORIZED",
            "none": "TIDAK ADA DEVICE",
        }.get(state, state.upper())
        self.state_badge.setText(status_text)
        self.state_badge.setProperty("status", state)
        self.state_badge.style().unpolish(self.state_badge)
        self.state_badge.style().polish(self.state_badge)
        name = self._device_name(info, serial)
        self.device_name.setText(name)
        self.serial_label.setText(serial or "Pilih perangkat untuk melihat detailnya.")
        self.mockup.set_device_info(info, state)
        self._update_details(info)

    @staticmethod
    def _device_name(info: DeviceInfo | None, serial: str | None) -> str:
        if info is not None:
            return info.model or info.brand or info.product_name or info.serial
        return serial or "Perangkat"

    def _update_details(self, info: DeviceInfo | None) -> None:
        values = {
            "brand": info.brand if info else None,
            "model": info.model if info else None,
            "product": info.product_name if info else None,
            "android": info.android_version if info else None,
            "api": str(info.api_level) if info and info.api_level is not None else None,
            "chipset": info.chipset if info else None,
            "abi": info.cpu_abi if info else None,
            "resolution": (
                f"{info.screen_w} × {info.screen_h}"
                if info and info.screen_w is not None and info.screen_h is not None
                else None
            ),
            "density": f"{info.density} dpi" if info and info.density is not None else None,
            "ram": f"{info.ram_gb:g} GB" if info and info.ram_gb is not None else None,
        }
        for key, value in values.items():
            self._rows[key].setText(value or "—")

        if info is None or info.battery_level is None:
            self.battery_bar.setVisible(False)
            self.battery_status.setVisible(False)
            return
        level = max(0, min(100, info.battery_level))
        self.battery_bar.setValue(level)
        self.battery_bar.setVisible(True)
        if info.charging is True:
            status = "Sedang mengisi daya"
        elif info.charging is False:
            status = "Tidak mengisi daya"
        else:
            status = ""
        self.battery_status.setText(status)
        self.battery_status.setVisible(bool(status))
