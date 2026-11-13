from dataclasses import asdict, dataclass

from super_adb.models.app_settings import ThemeMode


@dataclass(frozen=True, slots=True)
class ThemeTokens:
    bg: str
    surface: str
    raised: str
    border: str
    text: str
    muted: str
    accent: str
    accent_text: str
    success: str
    success_text: str
    warning: str
    warning_text: str
    danger: str
    danger_text: str

    def as_qss(self) -> dict[str, str]:
        return asdict(self)


THEMES: dict[str, ThemeTokens] = {
    "dark": ThemeTokens(
        bg="#0E0E0F",
        surface="#151516",
        raised="#1C1C1E",
        border="#2A2A2D",
        text="#ECECEE",
        muted="#8B8B92",
        accent="#4C8DFF",
        accent_text="#08111F",
        success="#3DCF8E",
        success_text="#3DCF8E",
        warning="#F5A524",
        warning_text="#F5A524",
        danger="#F2555A",
        danger_text="#F2555A",
    ),
    "light": ThemeTokens(
        bg="#F4F4F6",
        surface="#FFFFFF",
        raised="#FFFFFF",
        border="#E3E3E7",
        text="#18181B",
        muted="#6B6B73",
        accent="#2F6FEB",
        accent_text="#FFFFFF",
        success="#3DCF8E",
        success_text="#137A52",
        warning="#F5A524",
        warning_text="#8A5800",
        danger="#F2555A",
        danger_text="#B4232D",
    ),
}


def tokens_for(mode: ThemeMode) -> ThemeTokens:
    return THEMES["light"] if mode == "light" else THEMES["dark"]
