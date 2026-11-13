from dataclasses import dataclass
from typing import Literal

LogKind = Literal["command", "output", "error", "info"]


@dataclass(frozen=True, slots=True)
class LogEntry:
    kind: LogKind
    text: str
