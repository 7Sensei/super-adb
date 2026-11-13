from collections.abc import Callable
from typing import Literal

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFontMetrics, QResizeEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from super_adb.ui.icons import load_icon
from super_adb.ui.theme.manager import ThemeManager
from super_adb.ui.theme.tokens import ThemeTokens

ActionVariant = Literal["default", "primary", "danger"]


class ActionCard(QFrame):
    def __init__(
        self,
        action_id: str,
        title: str,
        description: str,
        icon_name: str,
        on_trigger: Callable[[], None],
        theme_manager: ThemeManager,
        variant: ActionVariant = "default",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("actionCard")
        self.setMinimumHeight(72)
        self.setMaximumHeight(96)
        self._icon_name = icon_name
        self._theme_manager = theme_manager
        self._variant = variant
        self._title_text = title
        self._description_text = description

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        self._icon = QLabel(self)
        self._icon.setObjectName("actionIcon")
        self._icon.setFixedSize(38, 38)
        layout.addWidget(self._icon)

        details = QVBoxLayout()
        details.setContentsMargins(0, 0, 0, 0)
        details.setSpacing(4)
        self._title = QLabel(title, self)
        self._title.setObjectName("actionTitle")
        self._title.setWordWrap(False)
        self._title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        details.addWidget(self._title)

        self._description = QLabel(description, self)
        self._description.setObjectName("actionDescription")
        self._description.setWordWrap(False)
        self._description.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Preferred,
        )
        self._description.setToolTip(description)
        details.addWidget(self._description)
        layout.addLayout(details, 1)

        self.button = QPushButton("Jalankan", self)
        self.button.setObjectName(f"action-{action_id}")
        self.button.setProperty("variant", variant)
        self.button.style().unpolish(self.button)
        self.button.style().polish(self.button)
        self.button.clicked.connect(on_trigger)
        layout.addWidget(self.button)

        theme_manager.themeChanged.connect(self._set_icon)
        self._set_icon(theme_manager.tokens)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        metrics = QFontMetrics(self._title.font())
        self._title.setText(
            metrics.elidedText(self._title_text, Qt.TextElideMode.ElideRight, self._title.width())
        )
        metrics = QFontMetrics(self._description.font())
        self._description.setText(
            metrics.elidedText(
                self._description_text,
                Qt.TextElideMode.ElideRight,
                self._description.width(),
            )
        )

    def set_variant(self, variant: ActionVariant) -> None:
        if variant == self._variant:
            return
        self._variant = variant
        self.button.setProperty("variant", variant)
        self.button.style().unpolish(self.button)
        self.button.style().polish(self.button)
        self._set_icon(self._theme_manager.tokens)

    def _set_icon(self, tokens: ThemeTokens) -> None:
        color = tokens.danger if self._variant == "danger" else tokens.accent
        icon = load_icon(self._icon_name, color, size=22)
        self._icon.setPixmap(icon.pixmap(QSize(22, 22)))
