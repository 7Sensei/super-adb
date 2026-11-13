from collections.abc import Callable
from typing import Literal

from PySide6.QtCore import QSize
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
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
        self.setMinimumHeight(148)
        self._icon_name = icon_name
        self._theme_manager = theme_manager
        self._variant = variant

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(9)

        heading = QHBoxLayout()
        heading.setSpacing(10)
        self._icon = QLabel(self)
        self._icon.setObjectName("actionIcon")
        self._icon.setFixedSize(38, 38)
        heading.addWidget(self._icon)

        name = QLabel(title, self)
        name.setObjectName("actionTitle")
        name.setWordWrap(True)
        heading.addWidget(name, 1)
        layout.addLayout(heading)

        detail = QLabel(description, self)
        detail.setObjectName("actionDescription")
        detail.setWordWrap(True)
        layout.addWidget(detail, 1)

        self.button = QPushButton("Jalankan", self)
        self.button.setObjectName(f"action-{action_id}")
        self.button.setProperty("variant", variant)
        self.button.style().unpolish(self.button)
        self.button.style().polish(self.button)
        self.button.clicked.connect(on_trigger)
        layout.addWidget(self.button)

        theme_manager.themeChanged.connect(self._set_icon)
        self._set_icon(theme_manager.tokens)

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
