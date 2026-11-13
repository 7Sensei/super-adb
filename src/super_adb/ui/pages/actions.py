from collections.abc import Callable
from typing import TypeAlias

from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QGridLayout, QScrollArea, QVBoxLayout, QWidget

from super_adb.ui.theme.manager import ThemeManager
from super_adb.ui.widgets.action_card import ActionCard, ActionVariant

ActionDefinition: TypeAlias = tuple[
    str,
    str,
    str,
    str,
    Callable[[], None],
    ActionVariant,
]


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
        self._grid = QGridLayout(content)
        self._grid.setContentsMargins(4, 4, 8, 8)
        self._grid.setHorizontalSpacing(12)
        self._grid.setVerticalSpacing(12)
        self._grid.setColumnStretch(0, 1)
        self._grid.setColumnStretch(1, 1)
        self._cards: list[ActionCard] = []
        self._columns = 2
        for index, (action_id, title, description, icon, callback, variant) in enumerate(actions):
            card = ActionCard(
                action_id,
                title,
                description,
                icon,
                callback,
                theme_manager,
                variant,
                content,
            )
            self._cards.append(card)
            self._grid.addWidget(card, index // self._columns, index % self._columns)
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        columns = 2 if self.width() >= 720 else 1
        if columns == self._columns:
            return
        self._columns = columns
        for index, card in enumerate(self._cards):
            self._grid.removeWidget(card)
            self._grid.addWidget(card, index // columns, index % columns)
