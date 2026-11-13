from collections.abc import Callable

from super_adb.models.app_settings import AppSettings, ThemeMode
from super_adb.services.settings_store import SettingsStore
from super_adb.viewmodels.base import Observable


class SettingsViewModel:
    def __init__(self, store: SettingsStore) -> None:
        self._store = store
        settings = store.load()
        self.theme_mode: Observable[ThemeMode] = Observable(settings.theme_mode)
        self.font_family: Observable[str] = Observable(settings.font_family)
        self._theme_applier: Callable[[ThemeMode], None] | None = None
        self._font_applier: Callable[[str], None] | None = None

    def bind_theme_applier(self, apply_theme: Callable[[ThemeMode], None]) -> None:
        self._theme_applier = apply_theme
        apply_theme(self.theme_mode.value)

    def bind_font_applier(self, apply_font: Callable[[str], None]) -> None:
        self._font_applier = apply_font
        apply_font(self.font_family.value)

    def set_theme_mode(self, mode: ThemeMode) -> None:
        if mode not in {"light", "dark", "system"}:
            raise ValueError(f"Mode tema tidak dikenal: {mode!r}")
        if mode == self.theme_mode.value:
            return
        self.theme_mode.value = mode
        self._save()
        if self._theme_applier is not None:
            self._theme_applier(mode)

    def set_font_family(self, family: str) -> None:
        if not family:
            raise ValueError("Nama font tidak boleh kosong.")
        if family != self.font_family.value:
            self.font_family.value = family
            self._save()
        if self._font_applier is not None:
            self._font_applier(family)

    def _save(self) -> None:
        self._store.save(
            AppSettings(
                theme_mode=self.theme_mode.value,
                font_family=self.font_family.value,
            )
        )
