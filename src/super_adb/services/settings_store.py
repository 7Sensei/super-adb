import json
import os
from pathlib import Path
from typing import Protocol

from super_adb.models.app_settings import AppSettings


class SettingsStore(Protocol):
    def load(self) -> AppSettings:
        """Load persisted application settings."""

    def save(self, settings: AppSettings) -> None:
        """Persist application settings."""


class JsonSettingsStore:
    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            appdata = os.environ.get("APPDATA")
            if not appdata:
                raise OSError("Environment variable APPDATA belum tersedia.")
            path = Path(appdata) / "super-adb" / "settings.json"
        self._path = path

    def load(self) -> AppSettings:
        if not self._path.exists():
            return AppSettings()
        data = json.loads(self._path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"Format pengaturan tidak valid: {self._path}")
        theme_mode = data.get("theme_mode", "dark")
        font_family = data.get("font_family", "Poppins")
        if theme_mode not in {"light", "dark", "system"}:
            raise ValueError(f"Mode tema tidak valid di {self._path}: {theme_mode!r}")
        if not isinstance(font_family, str) or not font_family:
            raise ValueError(f"Nama font tidak valid di {self._path}.")
        return AppSettings(theme_mode=theme_mode, font_family=font_family)

    def save(self, settings: AppSettings) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(
                {
                    "theme_mode": settings.theme_mode,
                    "font_family": settings.font_family,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
