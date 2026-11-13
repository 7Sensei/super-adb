from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from super_adb.ui.theme.manager import ThemeManager
from super_adb.viewmodels.settings_viewmodel import SettingsViewModel


class SettingsPage(QWidget):
    def __init__(
        self,
        viewmodel: SettingsViewModel,
        theme_manager: ThemeManager,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._viewmodel = viewmodel
        self._theme_manager = theme_manager
        self._fonts = sorted(
            (family for family in QFontDatabase.families() if not family.startswith("@")),
            key=str.casefold,
        )[:150]

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 8, 8)
        layout.setSpacing(12)

        appearance = QFrame(self)
        appearance.setObjectName("settingsCard")
        appearance_layout = QVBoxLayout(appearance)
        appearance_layout.setContentsMargins(16, 14, 16, 14)
        appearance_layout.setSpacing(8)
        appearance_title = QLabel("Tema", appearance)
        appearance_title.setObjectName("actionTitle")
        appearance_layout.addWidget(appearance_title)
        appearance_layout.addWidget(
            QLabel("Pilih tema terang, gelap, atau ikuti sistem.", appearance)
        )
        self.theme_selector = QComboBox(appearance)
        self.theme_selector.setObjectName("themeSelector")
        self.theme_selector.addItem("Terang", "light")
        self.theme_selector.addItem("Gelap", "dark")
        self.theme_selector.addItem("Sistem", "system")
        current_theme = self.theme_selector.findData(viewmodel.theme_mode.value)
        self.theme_selector.setCurrentIndex(current_theme)
        self.theme_selector.currentIndexChanged.connect(self._theme_changed)
        appearance_layout.addWidget(self.theme_selector)
        layout.addWidget(appearance)

        font_card = QFrame(self)
        font_card.setObjectName("settingsCard")
        font_layout = QVBoxLayout(font_card)
        font_layout.setContentsMargins(16, 14, 16, 14)
        font_layout.setSpacing(8)
        font_title = QLabel("Font", font_card)
        font_title.setObjectName("actionTitle")
        font_layout.addWidget(font_title)
        font_layout.addWidget(QLabel("Cari dan pilih font untuk aplikasi.", font_card))
        self.font_search = QLineEdit(font_card)
        self.font_search.setObjectName("fontSearch")
        self.font_search.setPlaceholderText("Ketik nama font...")
        self.font_search.textChanged.connect(self._filter_fonts)
        font_layout.addWidget(self.font_search)
        self.current_font = QLabel(f"Font aktif: {viewmodel.font_family.value}", font_card)
        self.current_font.setObjectName("mutedText")
        font_layout.addWidget(self.current_font)
        self.font_list = QListWidget(font_card)
        self.font_list.setObjectName("fontList")
        self.font_list.setMaximumHeight(220)
        self.font_list.itemClicked.connect(self._select_font)
        font_layout.addWidget(self.font_list)
        layout.addWidget(font_card)
        layout.addStretch(1)
        self._filter_fonts("")
        self._unsubscribe_font = viewmodel.font_family.subscribe(self._font_changed)
        self._unsubscribe_theme = viewmodel.theme_mode.subscribe(self._theme_mode_changed)

    def dispose(self) -> None:
        self._unsubscribe_font()
        self._unsubscribe_theme()

    def _theme_changed(self, index: int) -> None:
        mode = self.theme_selector.itemData(index)
        if mode in {"light", "dark", "system"}:
            self._viewmodel.set_theme_mode(mode)

    def _theme_mode_changed(self, mode: str) -> None:
        blocker = QSignalBlocker(self.theme_selector)
        self.theme_selector.setCurrentIndex(self.theme_selector.findData(mode))
        del blocker

    def _filter_fonts(self, query: str) -> None:
        self.font_list.clear()
        normalized_query = query.casefold()
        for family in self._fonts:
            if normalized_query in family.casefold():
                item = QListWidgetItem(family)
                item.setData(Qt.ItemDataRole.UserRole, family)
                self.font_list.addItem(item)
        self.font_list.setVisible(self.font_list.count() > 0)

    def _select_font(self, item: QListWidgetItem) -> None:
        family = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(family, str):
            self._viewmodel.set_font_family(family)

    def _font_changed(self, family: str) -> None:
        self.current_font.setText(f"Font aktif: {family}")
