from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DeviceInfo:
    serial: str
    state: str
    brand: str | None = None
    model: str | None = None
    product_name: str | None = None
    android_version: str | None = None
    api_level: int | None = None
    chipset: str | None = None
    cpu_abi: str | None = None
    screen_w: int | None = None
    screen_h: int | None = None
    density: int | None = None
    ram_gb: float | None = None
    battery_level: int | None = None
    charging: bool | None = None
