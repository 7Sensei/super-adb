from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from super_adb.models.device_info import DeviceInfo
from super_adb.ui.theme.manager import ThemeManager
from super_adb.ui.theme.tokens import ThemeTokens


class DeviceMockup(QWidget):
    def __init__(
        self,
        theme_manager: ThemeManager,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("deviceMockup")
        self.setMinimumHeight(180)
        self.setMaximumHeight(340)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self._theme_manager = theme_manager
        self._device_info: DeviceInfo | None = None
        theme_manager.themeChanged.connect(self._theme_changed)

    def sizeHint(self) -> QSize:
        return QSize(260, 240)

    def set_device_info(self, info: DeviceInfo | None) -> None:
        self._device_info = info
        self.update()

    def paintEvent(self, event) -> None:
        tokens = self._theme_manager.tokens
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        device_width = min(112.0, self.width() * 0.48)
        device_height = min(184.0, self.height() - 12.0)
        left = (self.width() - device_width) / 2
        top = (self.height() - device_height) / 2
        body = QRectF(left, top, device_width, device_height)
        body_path = QPainterPath()
        body_path.addRoundedRect(body, 19, 19)
        painter.setPen(QPen(QColor(tokens.border), 2))
        painter.setBrush(QColor(tokens.raised))
        painter.drawPath(body_path)

        screen = body.adjusted(6, 8, -6, -8)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(tokens.bg))
        painter.drawRoundedRect(screen, 14, 14)

        notch = QRectF(
            screen.center().x() - 17,
            screen.top() + 5,
            34,
            5,
        )
        painter.setBrush(QColor(tokens.border))
        painter.drawRoundedRect(notch, 3, 3)

        center = QRectF(screen.left() + 5, screen.center().y() - 22, screen.width() - 10, 48)
        painter.setPen(QColor(tokens.text))
        font = QFont(self.font())
        font.setBold(True)
        painter.setFont(font)
        label = self._device_name()
        painter.drawText(
            center,
            Qt.AlignmentFlag.AlignCenter,
            QFontMetrics(font).elidedText(label, Qt.TextElideMode.ElideRight, int(center.width())),
        )

        home_indicator = QRectF(screen.center().x() - 14, screen.bottom() - 10, 28, 3)
        painter.setBrush(QColor(tokens.muted))
        painter.drawRoundedRect(home_indicator, 2, 2)
        painter.end()

    def _device_name(self) -> str:
        if self._device_info is None:
            return "Android"
        return (
            self._device_info.model
            or self._device_info.brand
            or self._device_info.product_name
            or self._device_info.serial
        )

    def _theme_changed(self, tokens: ThemeTokens) -> None:
        self.update()
