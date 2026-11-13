from PySide6.QtCore import QSignalBlocker, Qt, QTimer
from PySide6.QtGui import QFont, QFontDatabase, QFontInfo
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
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
        families = QFontDatabase.families(QFontDatabase.WritingSystem.Latin)
        unique_families = {
            family.casefold(): family
            for family in families
            if not family.startswith("@")
        }
        self._fonts = sorted(
            unique_families.values(),
            key=str.casefold,
        )
        self._preview_family: str | None = None
        self._applying_font = False
        self._pending_font_family: str | None = None
        self._previous_font: QFont | None = None
        self._previous_theme_font_family: str | None = None

        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(self)
        scroll.setObjectName("settingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget(scroll)
        content.setObjectName("settingsContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(4, 4, 8, 8)
        layout.setSpacing(12)

        appearance = QFrame(content)
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
        self.theme_selector.addItem("Ikuti sistem", "system")
        current_theme = self.theme_selector.findData(viewmodel.theme_mode.value)
        self.theme_selector.setCurrentIndex(current_theme)
        self.theme_selector.currentIndexChanged.connect(self._theme_changed)
        appearance_layout.addWidget(self.theme_selector)
        layout.addWidget(appearance)

        font_card = QFrame(content)
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

        application = QApplication.instance()
        self._font_application = (
            application if isinstance(application, QApplication) else None
        )
        active_family = (
            self._font_application.font().family()
            if self._font_application is not None
            else "Segoe UI"
        )
        self.current_font = QLabel(font_card)
        self.current_font.setObjectName("mutedText")
        font_layout.addWidget(self.current_font)

        self.preview = QLabel("Pilih font untuk pratinjau.", font_card)
        self.preview.setObjectName("fontPreview")
        font_layout.addWidget(self.preview)

        self.font_list = QListWidget(font_card)
        self.font_list.setObjectName("fontList")
        self.font_list.setMinimumHeight(240)
        self.font_list.setUniformItemSizes(True)
        self.font_list.currentItemChanged.connect(self._select_font)
        font_layout.addWidget(self.font_list)
        self._font_items: dict[str, QListWidgetItem] = {}
        for family in self._fonts:
            item = QListWidgetItem(family)
            item.setData(Qt.ItemDataRole.UserRole, family)
            self.font_list.addItem(item)
            self._font_items[family] = item

        buttons = QWidget(font_card)
        buttons_layout = QHBoxLayout(buttons)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.apply_font_button = QPushButton("Terapkan", buttons)
        self.apply_font_button.setObjectName("applyFont")
        self.apply_font_button.clicked.connect(self._apply_selected_font)
        buttons_layout.addWidget(self.apply_font_button)
        self.default_font_button = QPushButton("Kembalikan default", buttons)
        self.default_font_button.setObjectName("defaultFont")
        self.default_font_button.clicked.connect(self._restore_default_font)
        buttons_layout.addWidget(self.default_font_button)
        font_layout.addWidget(buttons)
        layout.addWidget(font_card)
        layout.addStretch(1)

        scroll.setWidget(content)
        page_layout.addWidget(scroll)
        self._filter_fonts("")
        self._update_active_font(active_family)
        self._font_changed_connection = None
        if self._font_application is not None:
            self._font_changed_connection = self._font_application.fontChanged.connect(
                self._application_font_changed
            )
        self._unsubscribe_theme = viewmodel.theme_mode.subscribe(self._theme_mode_changed)

    def dispose(self) -> None:
        self._unsubscribe_theme()
        if self._font_application is not None and self._font_changed_connection is not None:
            self._font_application.fontChanged.disconnect(self._font_changed_connection)

    def _theme_changed(self, index: int) -> None:
        mode = self.theme_selector.itemData(index)
        if mode in {"light", "dark", "system"}:
            self._viewmodel.set_theme_mode(mode)

    def _theme_mode_changed(self, mode: str) -> None:
        blocker = QSignalBlocker(self.theme_selector)
        self.theme_selector.setCurrentIndex(self.theme_selector.findData(mode))
        del blocker

    def _filter_fonts(self, query: str) -> None:
        normalized_query = query.casefold()
        visible_count = 0
        for family, item in self._font_items.items():
            visible = normalized_query in family.casefold()
            item.setHidden(not visible)
            visible_count += visible
        self.font_list.setVisible(visible_count > 0)
        if self._preview_family is not None:
            selected_item = self._font_items.get(self._preview_family)
            if selected_item is not None and not selected_item.isHidden():
                self.font_list.setCurrentItem(selected_item)

    def _select_font(
        self,
        item: QListWidgetItem | None,
        previous: QListWidgetItem | None,
    ) -> None:
        del previous
        family = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        if not isinstance(family, str):
            return
        self._preview_family = family
        self.preview.setText("Pratinjau: The quick brown fox 0123456789")
        self.preview.setFont(QFont(family, self.preview.font().pointSize()))

    def _apply_selected_font(self) -> None:
        self._apply_font_family(self._preview_family)

    def _restore_default_font(self) -> None:
        family = "Poppins" if QFontDatabase.hasFamily("Poppins") else "Segoe UI"
        self._apply_font_family(family)

    def _apply_font_family(self, family: str | None) -> None:
        if (
            family is None
            or self._applying_font
            or self._font_application is None
        ):
            return
        self._applying_font = True
        self._pending_font_family = family
        self._previous_font = self._font_application.font()
        self._previous_theme_font_family = self._theme_manager.font_family
        self.apply_font_button.setEnabled(False)
        self.default_font_button.setEnabled(False)
        self.font_search.setEnabled(False)
        self.font_list.setEnabled(False)
        self.apply_font_button.setText("Menerapkan...")
        self.current_font.setText("Menerapkan...")
        QTimer.singleShot(0, self._finish_font_application)

    def _finish_font_application(self) -> None:
        family = self._pending_font_family
        previous_font = self._previous_font
        previous_theme_family = self._previous_theme_font_family
        if family is None or previous_font is None or self._font_application is None:
            self._finish_font_feedback()
            return
        try:
            self._theme_manager.set_font_family(family)
            effective_family = QFontInfo(self._font_application.font()).family()
            if effective_family != family:
                self._restore_previous_font(previous_font, previous_theme_family)
                self.current_font.setText(f"Font {family} tidak dapat diterapkan")
                return
            self._viewmodel.save_font_family(family)
            self._update_active_font(effective_family)
        except (OSError, RuntimeError, ValueError) as error:
            self._restore_previous_font(previous_font, previous_theme_family)
            self.current_font.setText(f"Gagal menerapkan font {family}: {error}")
            raise
        finally:
            self._finish_font_feedback()

    def _restore_previous_font(
        self,
        font: QFont,
        theme_font_family: str | None,
    ) -> None:
        if self._font_application is not None:
            self._font_application.setFont(font)
        if theme_font_family is not None:
            self._theme_manager.font_family = theme_font_family

    def _finish_font_feedback(self) -> None:
        self._applying_font = False
        self._pending_font_family = None
        self._previous_font = None
        self._previous_theme_font_family = None
        self.apply_font_button.setText("Terapkan")
        self.apply_font_button.setEnabled(True)
        self.default_font_button.setEnabled(True)
        self.font_search.setEnabled(True)
        self.font_list.setEnabled(True)

    def _application_font_changed(self, font: QFont) -> None:
        if not self._applying_font:
            self._update_active_font(font.family())

    def _update_active_font(self, active_family: str) -> None:
        saved_family = self._viewmodel.font_family.value
        if QFontDatabase.hasFamily(saved_family):
            text = f"Font aktif: {active_family}"
        else:
            text = f"Font aktif: {saved_family} (tidak tersedia, memakai {active_family})"
        self.current_font.setText(text)
