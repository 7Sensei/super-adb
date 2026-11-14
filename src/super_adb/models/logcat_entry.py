from dataclasses import dataclass
from typing import Literal

LogcatLevel = Literal["V", "D", "I", "W", "E", "F", "M"]


@dataclass(frozen=True, slots=True)
class LogcatEntry:
    seq: int
    time: str | None
    pid: int | None
    tid: int | None
    level: LogcatLevel
    tag: str
    message: str
    raw: str
