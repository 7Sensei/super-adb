import io
import subprocess
from unittest.mock import patch

import pytest

from super_adb.services.adb_service import SubprocessAdbService
from super_adb.services.errors import AdbError, AdbNotFoundError


class FakeProcess:
    def __init__(self, output: str, returncode: int = 0) -> None:
        self.stdout = io.StringIO(output)
        self.returncode = returncode

    def __enter__(self) -> "FakeProcess":
        return self

    def __exit__(self, *args: object) -> None:
        self.stdout.close()

    def wait(self) -> int:
        return self.returncode


def test_execute_finds_adb_streams_lines_and_returns_output() -> None:
    process = FakeProcess("List of devices attached\nserial-1\tdevice\n")
    lines: list[str] = []
    with (
        patch("super_adb.services.adb_service.shutil.which", return_value="C:/platform/adb.exe"),
        patch("super_adb.services.adb_service.subprocess.Popen", return_value=process) as popen,
    ):
        output = SubprocessAdbService().execute(["adb", "devices"], lines.append)

    assert output == "List of devices attached\nserial-1\tdevice"
    assert lines == ["List of devices attached", "serial-1\tdevice"]
    assert popen.call_args.args[0] == ["C:/platform/adb.exe", "devices"]
    assert popen.call_args.kwargs.get("shell", False) is False
    assert popen.call_args.kwargs["creationflags"] == getattr(subprocess, "CREATE_NO_WINDOW", 0)


def test_execute_reports_adb_not_found() -> None:
    with patch("super_adb.services.adb_service.shutil.which", return_value=None):
        with pytest.raises(AdbNotFoundError, match="ADB tidak ditemukan"):
            SubprocessAdbService().execute(["adb", "devices"], lambda line: None)


@pytest.mark.parametrize(
    ("output", "returncode", "expected"),
    [
        ("error: device offline", 1, "offline"),
        ("error: device unauthorized", 1, "diotorisasi"),
        ("unknown command", 2, "kode 2"),
    ],
)
def test_execute_reports_command_failures(output: str, returncode: int, expected: str) -> None:
    with (
        patch("super_adb.services.adb_service.shutil.which", return_value="adb"),
        patch(
            "super_adb.services.adb_service.subprocess.Popen",
            return_value=FakeProcess(output, returncode),
        ),
    ):
        with pytest.raises(AdbError, match=expected):
            SubprocessAdbService().execute(["adb", "shell", "getprop"], lambda line: None)


def test_execute_rejects_non_list_command() -> None:
    with pytest.raises(AdbError, match="list"):
        SubprocessAdbService().execute("adb devices", lambda line: None)  # type: ignore[arg-type]
