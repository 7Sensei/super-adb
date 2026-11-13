from dataclasses import dataclass
from typing import Literal

ThemeMode = Literal["light", "dark", "system"]


@dataclass(frozen=True, slots=True)
class AppSettings:
    theme_mode: ThemeMode = "dark"
    font_family: str = "Poppins"
