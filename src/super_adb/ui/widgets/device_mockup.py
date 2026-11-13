from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
)
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
        self._device_state = "none"
        theme_manager.themeChanged.connect(self._theme_changed)

    def sizeHint(self) -> QSize:
        return QSize(260, 240)

    @property
    def device_state(self) -> str:
        return self._device_state

    def set_device_info(self, info: DeviceInfo | None, state: str = "none") -> None:
        self._device_info = info
        self._device_state = state
        self.update()

    def paintEvent(self, event) -> None:
        tokens = self._theme_manager.tokens
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        device_height = min(self.height() - 8.0, self.width() * 21 / 9)
        device_width = device_height * 9 / 19
        body = QRectF(
            (self.width() - device_width) / 2,
            (self.height() - device_height) / 2,
            device_width,
            device_height,
        )
        body_path = QPainterPath()
        body_path.addRoundedRect(body, 22, 22)

        frame_gradient = QLinearGradient(body.topLeft(), body.bottomRight())
        frame_gradient.setColorAt(0, QColor(tokens.raised).lighter(112))
        frame_gradient.setColorAt(1, QColor(tokens.border))
        painter.setPen(QPen(QColor(tokens.border), 2))
        painter.setBrush(frame_gradient)
        painter.drawPath(body_path)

        screen = body.adjusted(7, 10, -7, -10)
        screen_path = QPainterPath()
        screen_path.addRoundedRect(screen, 17, 17)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(tokens.bg))
        painter.drawPath(screen_path)

        painter.save()
        painter.setClipPath(screen_path)
        notch = QRectF(screen.center().x() - 18, screen.top() + 6, 36, 5)
        painter.setBrush(QColor(tokens.border))
        painter.drawRoundedRect(notch, 3, 3)

        if self._device_state != "device":
            self._draw_status(painter, screen, tokens)
        else:
            self._draw_device_details(painter, screen, tokens)

        home_indicator = QRectF(screen.center().x() - 16, screen.bottom() - 9, 32, 3)
        painter.setBrush(QColor(tokens.muted))
        painter.drawRoundedRect(home_indicator, 2, 2)
        painter.restore()
        painter.end()

    def _draw_status(self, painter: QPainter, screen: QRectF, tokens: ThemeTokens) -> None:
        labels = {
            "offline": ("OFFLINE", tokens.warning_text),
            "unauthorized": ("UNAUTHORIZED", tokens.danger_text),
            "none": ("TIDAK ADA DEVICE", tokens.muted),
        }
        label, color = labels.get(self._device_state, (self._device_state.upper(), tokens.muted))
        font = QFont(self.font())
        font.setPointSizeF(7.5)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(color))
        center = QRectF(screen.left() + 4, screen.center().y() - 15, screen.width() - 8, 30)
        painter.drawText(
            center,
            Qt.AlignmentFlag.AlignCenter,
            QFontMetrics(font).elidedText(label, Qt.TextElideMode.ElideRight, int(center.width())),
        )

    def _draw_device_details(
        self,
        painter: QPainter,
        screen: QRectF,
        tokens: ThemeTokens,
    ) -> None:
        info = self._device_info
        font = QFont(self.font())
        font.setPointSizeF(8)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(tokens.muted))
        content_width = screen.width() - 16
        left = screen.left() + 8
        brand = info.brand if info and info.brand else "Android"
        model = info.model or info.product_name or "Android" if info else "Android"
        brand_rect = QRectF(left, screen.top() + 24, content_width, 15)
        model_rect = QRectF(left, screen.top() + 39, content_width, 20)
        painter.drawText(
            brand_rect,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            QFontMetrics(font).elidedText(brand, Qt.TextElideMode.ElideRight, int(content_width)),
        )
        painter.setPen(QColor(tokens.text))
        painter.drawText(
            model_rect,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            QFontMetrics(font).elidedText(model, Qt.TextElideMode.ElideRight, int(content_width)),
        )

        version = info.android_version if info and info.android_version else "11"
        api_level = str(info.api_level) if info and info.api_level is not None else "30"
        android_font = QFont(font)
        android_font.setPointSizeF(6.5)
        android_font.setBold(False)
        painter.setFont(android_font)
        painter.setPen(QColor(tokens.muted))
        android_text = f"Android {version} - API {api_level}"
        android_rect = QRectF(left, screen.top() + 61, content_width, 16)
        painter.drawText(
            android_rect,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            QFontMetrics(android_font).elidedText(
                android_text,
                Qt.TextElideMode.ElideRight,
                int(content_width),
            ),
        )

        level = info.battery_level if info and info.battery_level is not None else 0
        battery = QRectF(left + 3, screen.bottom() - 36, content_width - 25, 8)
        painter.setPen(QPen(QColor(tokens.border), 1))
        painter.setBrush(QColor(tokens.raised))
        painter.drawRoundedRect(battery, 4, 4)
        fill = battery.adjusted(1, 1, -1, -1)
        fill.setWidth(fill.width() * max(0, min(100, level)) / 100)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(tokens.success))
        painter.drawRoundedRect(fill, 3, 3)

        percent_text = f"{level}%" if info and info.battery_level is not None else "--%"
        painter.setFont(android_font)
        painter.setPen(QColor(tokens.text))
        percent_rect = QRectF(battery.right() + 4, battery.top() - 3, 25, 14)
        painter.drawText(percent_rect, Qt.AlignmentFlag.AlignVCenter, percent_text)
        if info and info.charging is True:
            center_x = battery.left() - 7
            center_y = battery.center().y()
            bolt = QPolygonF(
                [
                    QPointF(center_x + 2, center_y - 6),
                    QPointF(center_x - 3, center_y + 1),
                    QPointF(center_x, center_y + 1),
                    QPointF(center_x - 2, center_y + 6),
                    QPointF(center_x + 4, center_y - 2),
                    QPointF(center_x + 1, center_y - 2),
                ]
            )
            painter.setBrush(QColor(tokens.warning))
            painter.drawPolygon(bolt)

    def _theme_changed(self, tokens: ThemeTokens) -> None:
        self.update()
