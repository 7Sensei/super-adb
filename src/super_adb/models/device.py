from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Device:
    serial: str
    state: str
