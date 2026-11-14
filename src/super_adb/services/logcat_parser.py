import re

from super_adb.models.logcat_entry import LogcatEntry, LogcatLevel

_THREADTIME_PATTERN = re.compile(
    r"^(?P<time>\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\s+"
    r"(?P<pid>\d+)\s+(?P<tid>\d+)\s+(?P<level>[VDIWEF])\s+"
    r"(?P<tag>.+?):[ \t]?(?P<message>.*)$"
)
_BUFFER_SEPARATOR_PATTERN = re.compile(r"^-{9} beginning of .+$")
_MAX_LINE_LENGTH = 4000


class LogcatParser:
    def __init__(self) -> None:
        self._sequence = 0
        self._last_thread_entry: LogcatEntry | None = None

    def parse_line(self, line: str) -> LogcatEntry | None:
        raw = line.rstrip("\r")
        if len(raw) > _MAX_LINE_LENGTH:
            raw = raw[: _MAX_LINE_LENGTH - 1] + "…"

        if _BUFFER_SEPARATOR_PATTERN.match(raw):
            return self._entry(
                time=None,
                pid=None,
                tid=None,
                level="M",
                tag="",
                message=raw,
                raw=raw,
            )

        match = _THREADTIME_PATTERN.match(raw)
        if match is not None:
            entry = self._entry(
                time=match.group("time"),
                pid=int(match.group("pid")),
                tid=int(match.group("tid")),
                level=match.group("level"),  # type: ignore[arg-type]
                tag=match.group("tag"),
                message=match.group("message"),
                raw=raw,
            )
            self._last_thread_entry = entry
            return entry

        if self._last_thread_entry is None:
            return None

        previous = self._last_thread_entry
        entry = self._entry(
            time=previous.time,
            pid=previous.pid,
            tid=previous.tid,
            level=previous.level,
            tag=previous.tag,
            message=raw,
            raw=raw,
        )
        self._last_thread_entry = entry
        return entry

    def parse_lines(self, lines: list[str]) -> list[LogcatEntry]:
        entries = []
        for line in lines:
            entry = self.parse_line(line)
            if entry is not None:
                entries.append(entry)
        return entries

    def reset_context(self) -> None:
        self._last_thread_entry = None

    def _entry(
        self,
        *,
        time: str | None,
        pid: int | None,
        tid: int | None,
        level: LogcatLevel,
        tag: str,
        message: str,
        raw: str,
    ) -> LogcatEntry:
        self._sequence += 1
        return LogcatEntry(
            seq=self._sequence,
            time=time,
            pid=pid,
            tid=tid,
            level=level,
            tag=tag,
            message=message,
            raw=raw,
        )
