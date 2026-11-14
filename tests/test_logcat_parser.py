from pathlib import Path

from super_adb.models.logcat_entry import LogcatEntry
from super_adb.services.logcat_parser import LogcatParser

_FIXTURE = Path(__file__).parent / "fixtures" / "logcat_threadtime.txt"


def test_parser_reads_synthetic_threadtime_fixture() -> None:
    entries = LogcatParser().parse_lines(_FIXTURE.read_text(encoding="utf-8").splitlines())

    assert len(entries) == 6
    assert entries[0].level == "M"
    assert entries[0].message == "--------- beginning of main"
    assert entries[1] == LogcatEntry(
        seq=2,
        time="06-15 14:32:10.123",
        pid=2147,
        tid=2189,
        level="I",
        tag="Activity Manager",
        message="Activity resumed",
        raw="06-15 14:32:10.123  2147  2189 I Activity Manager: Activity resumed",
    )
    assert entries[2].tag == "Custom Tag"
    assert entries[2].message == ""
    assert entries[3].pid == 9876543210
    assert entries[3].message.endswith("日本語 and 😀")
    assert entries[5].level == "E"
    assert entries[5].tag == "Multi Line Tag"
    assert entries[5].message == "    continuation detail"


def test_parser_ignores_damaged_prefix_and_uses_valid_entry_for_continuation() -> None:
    parser = LogcatParser()

    assert parser.parse_line("not a threadtime entry") is None
    parsed = parser.parse_lines(
        [
            "06-15 14:32:10.123  7  8 V Test Tag: first",
            "broken continuation",
        ]
    )

    assert [entry.message for entry in parsed] == ["first", "broken continuation"]
    assert parsed[1].pid == 7
    assert parsed[1].tag == "Test Tag"
    assert parsed[1].level == "V"
    assert parsed[1].time == parsed[0].time


def test_parser_drops_trailing_carriage_return_and_truncates_long_lines() -> None:
    parser = LogcatParser()
    parsed = parser.parse_line("06-15 14:32:10.123 1 2 I Tag: " + ("x" * 5000) + "\r")

    assert parsed is not None
    assert len(parsed.raw) == 4000
    assert parsed.raw.endswith("…")
    assert parsed.message.endswith("…")
    assert "\r" not in parsed.raw


def test_parser_sequence_continues_after_context_reset() -> None:
    parser = LogcatParser()
    first = parser.parse_line("06-15 14:32:10.123 1 2 I Tag: first")
    parser.reset_context()

    assert parser.parse_line("orphaned continuation") is None
    second = parser.parse_line("06-15 14:32:10.124 1 2 I Tag: second")

    assert first is not None
    assert second is not None
    assert second.seq == first.seq + 1
