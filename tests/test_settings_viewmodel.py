from pathlib import Path

from super_adb.models.app_settings import AppSettings
from super_adb.services.settings_store import JsonSettingsStore
from super_adb.viewmodels.settings_viewmodel import SettingsViewModel


class FakeStore:
    def __init__(self, settings: AppSettings | None = None) -> None:
        self.settings = settings or AppSettings()
        self.saved: list[AppSettings] = []

    def load(self) -> AppSettings:
        return self.settings

    def save(self, settings: AppSettings) -> None:
        self.settings = settings
        self.saved.append(settings)


def test_settings_viewmodel_loads_and_persists_theme_and_font() -> None:
    store = FakeStore(AppSettings(theme_mode="dark", font_family="Poppins"))
    viewmodel = SettingsViewModel(store)

    viewmodel.set_theme_mode("light")
    viewmodel.set_font_family("Segoe UI")

    assert viewmodel.theme_mode.value == "light"
    assert viewmodel.font_family.value == "Segoe UI"
    assert store.saved == [
        AppSettings(theme_mode="light", font_family="Poppins"),
        AppSettings(theme_mode="light", font_family="Segoe UI"),
    ]


def test_json_settings_store_round_trips_settings(tmp_path: Path) -> None:
    store = JsonSettingsStore(tmp_path / "super-adb" / "settings.json")
    settings = AppSettings(theme_mode="system", font_family="Segoe UI")

    store.save(settings)

    assert store.load() == settings
