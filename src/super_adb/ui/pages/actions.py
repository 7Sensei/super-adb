from collections.abc import Callable
from typing import TypeAlias

from PySide6.QtWidgets import QGridLayout, QScrollArea, QVBoxLayout, QWidget

from super_adb.ui.theme.manager import ThemeManager
from super_adb.ui.widgets.action_card import ActionCard

ActionDefinition: TypeAlias = tuple[str, str, str, str, Callable[[], None]]


class ActionPage(QWidget):
    def __init__(
        self,
        actions: list[ActionDefinition],
        theme_manager: ThemeManager,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(self)
        scroll.setObjectName("actionPageScroll")
        scroll.setWidgetResizable(True)
        scroll.viewport().setObjectName("actionPageViewport")
        content = QWidget(scroll)
        content.setObjectName("actionPageContent")
        grid = QGridLayout(content)
        grid.setContentsMargins(4, 4, 8, 8)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        for index, (action_id, title, description, icon, callback) in enumerate(actions):
            card = ActionCard(
                action_id,
                title,
                description,
                icon,
                callback,
                theme_manager,
                content,
            )
            grid.addWidget(card, index // 2, index % 2)
        scroll.setWidget(content)
        layout.addWidget(scroll)
