from collections.abc import Callable

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


class ActionCard(QFrame):
    def __init__(
        self,
        action_id: str,
        title: str,
        description: str,
        icon_name: str,
        on_trigger: Callable[[], None],
        theme_manager: ThemeManager,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("actionCard")
        self.setMinimumHeight(148)
        self._icon_name = icon_name
        self._theme_manager = theme_manager

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
        self.button.clicked.connect(on_trigger)
        layout.addWidget(self.button)

        theme_manager.themeChanged.connect(self._set_icon)
        self._set_icon(theme_manager.tokens)

    def _set_icon(self, tokens: ThemeTokens) -> None:
        icon = load_icon(self._icon_name, tokens.accent, size=22)
        self._icon.setPixmap(icon.pixmap(QSize(22, 22)))
