from super_adb.models.app_settings import AppSettings, ThemeMode
from super_adb.services.settings_store import SettingsStore
from super_adb.viewmodels.base import Observable


class SettingsViewModel:
    def __init__(self, store: SettingsStore) -> None:
        self._store = store
        settings = store.load()
        self.theme_mode: Observable[ThemeMode] = Observable(settings.theme_mode)
        self.font_family: Observable[str] = Observable(settings.font_family)

    def set_theme_mode(self, mode: ThemeMode) -> None:
        if mode not in {"light", "dark", "system"}:
            raise ValueError(f"Mode tema tidak dikenal: {mode!r}")
        if mode == self.theme_mode.value:
            return
        self.theme_mode.value = mode
        self._save()

    def set_font_family(self, family: str) -> None:
        if not family:
            raise ValueError("Nama font tidak boleh kosong.")
        if family == self.font_family.value:
            return
        self.font_family.value = family
        self._save()

    def _save(self) -> None:
        self._store.save(
            AppSettings(
                theme_mode=self.theme_mode.value,
                font_family=self.font_family.value,
            )
        )
