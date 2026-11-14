import io
import subprocess
import threading
from unittest.mock import patch

import pytest

from super_adb.services.errors import AdbError, AdbNotFoundError
from super_adb.services.logcat_service import SubprocessLogcatService


class FakeProcess:
    def __init__(self, output: str, returncode: int = 0) -> None:
        self.stdout = io.StringIO(output)
        self.returncode = returncode
        self.terminate_calls = 0
        self.kill_calls = 0

    def poll(self) -> int:
        return self.returncode

    def wait(self, timeout: float | None = None) -> int:
        return self.returncode

    def terminate(self) -> None:
        self.terminate_calls += 1

    def kill(self) -> None:
        self.kill_calls += 1


class BlockingOutput:
    def __init__(self, process: "BlockingProcess") -> None:
        self.process = process

    def __iter__(self) -> "BlockingOutput":
        return self

    def __next__(self) -> str:
        self.process.finished.wait()
        raise StopIteration


class BlockingProcess:
    def __init__(self) -> None:
        self.stdout = BlockingOutput(self)
        self.started = threading.Event()
        self.finished = threading.Event()
        self.returncode: int | None = None
        self.terminate_calls = 0
        self.kill_calls = 0
        self.started.set()

    def poll(self) -> int | None:
        return self.returncode

    def wait(self, timeout: float | None = None) -> int:
        if not self.finished.wait(timeout):
            raise subprocess.TimeoutExpired("adb", timeout)
        return self.returncode or 0

    def terminate(self) -> None:
        self.terminate_calls += 1
        self.returncode = -15
        self.finished.set()

    def kill(self) -> None:
        self.kill_calls += 1
        self.returncode = -9
        self.finished.set()


def wait_for_end(event: threading.Event) -> None:
    assert event.wait(timeout=3)


def test_stream_argv_batches_thousands_of_lines_and_preserves_unicode() -> None:
    lines = [f"line {index} 😀 日本語" for index in range(10_000)]
    output = "\r\n".join(lines) + "\r\n"
    process = FakeProcess(output)
    batches: list[list[str]] = []
    ended = threading.Event()
    result: list[tuple[int, str | None]] = []

    def on_end(code: int, message: str | None) -> None:
        result.append((code, message))
        ended.set()

    with (
        patch("super_adb.services.logcat_service.shutil.which", return_value="C:/adb.exe"),
        patch(
            "super_adb.services.logcat_service.subprocess.Popen", return_value=process
        ) as popen,
    ):
        service = SubprocessLogcatService()
        service.start_stream("serial-1", batches.append, on_end)
        wait_for_end(ended)

    assert popen.call_args.args[0] == [
        "C:/adb.exe",
        "-s",
        "serial-1",
        "logcat",
        "-v",
        "threadtime",
        "-T",
        "500",
    ]
    assert popen.call_args.kwargs["encoding"] == "utf-8"
    assert popen.call_args.kwargs["errors"] == "replace"
    assert popen.call_args.kwargs.get("shell", False) is False
    assert sum(map(len, batches)) == 10_000
    assert len(batches) < 100
    assert batches[0][0] == "line 0 😀 日本語"
    assert result == [(0, "Aliran logcat berakhir.")]


def test_stream_retries_without_since_option_only_for_unsupported_option() -> None:
    processes = [
        FakeProcess("logcat: invalid option -- T\n", returncode=1),
        FakeProcess("06-15 14:32:10.123 1 2 I Test: ok\n"),
    ]
    calls: list[list[str]] = []

    def popen(command: list[str], **kwargs: object) -> FakeProcess:
        calls.append(command)
        return processes.pop(0)

    batches: list[list[str]] = []
    ended = threading.Event()
    with (
        patch("super_adb.services.logcat_service.shutil.which", return_value="adb"),
        patch("super_adb.services.logcat_service.subprocess.Popen", side_effect=popen),
    ):
        SubprocessLogcatService().start_stream(
            "serial-1", batches.append, lambda *_: ended.set()
        )
        wait_for_end(ended)

    assert calls == [
        ["adb", "-s", "serial-1", "logcat", "-v", "threadtime", "-T", "500"],
        ["adb", "-s", "serial-1", "logcat", "-v", "threadtime"],
    ]
    assert batches == [["06-15 14:32:10.123 1 2 I Test: ok"]]


def test_stream_stop_only_terminates_its_process_and_on_end_is_once() -> None:
    processes = [BlockingProcess(), BlockingProcess()]
    created = [threading.Event(), threading.Event()]
    end_events = [threading.Event(), threading.Event()]
    end_calls: list[list[tuple[int, str | None]]] = [[], []]
    next_process = 0

    def popen(*_args: object, **_kwargs: object) -> BlockingProcess:
        nonlocal next_process
        current = next_process
        next_process += 1
        created[current].set()
        return processes[current]

    service = SubprocessLogcatService()
    handles = []
    with (
        patch("super_adb.services.logcat_service.shutil.which", return_value="adb"),
        patch("super_adb.services.logcat_service.subprocess.Popen", side_effect=popen),
    ):
        for index, serial in enumerate(("serial-1", "serial-2")):
            handles.append(
                service.start_stream(
                    serial,
                    lambda _batch: None,
                    lambda code, message, index=index: (
                        end_calls[index].append((code, message)),
                        end_events[index].set(),
                    ),
                )
            )
        assert all(event.wait(timeout=2) for event in created)
        handles[0].stop()
        wait_for_end(end_events[0])

        assert end_calls[0] == [(-15, None)]
        assert processes[0].terminate_calls == 1
        assert end_events[1].is_set() is False
        assert processes[1].poll() is None

        handles[1].stop()
        wait_for_end(end_events[1])

    assert len(end_calls[0]) == len(end_calls[1]) == 1


def test_second_stream_for_same_device_is_rejected() -> None:
    process = BlockingProcess()
    end = threading.Event()
    with (
        patch("super_adb.services.logcat_service.shutil.which", return_value="adb"),
        patch("super_adb.services.logcat_service.subprocess.Popen", return_value=process),
    ):
        service = SubprocessLogcatService()
        handle = service.start_stream("serial-1", lambda _: None, lambda *_: end.set())
        with pytest.raises(AdbError, match="sudah berjalan"):
            service.start_stream("serial-1", lambda _: None, lambda *_: None)
        handle.stop()
        wait_for_end(end)


def test_dump_clear_argv_and_timeouts() -> None:
    completed = subprocess.CompletedProcess(args=[], returncode=0, stdout="one\r\ntwo\r\n")
    with (
        patch("super_adb.services.logcat_service.shutil.which", return_value="C:/adb.exe"),
        patch("super_adb.services.logcat_service.subprocess.run", return_value=completed) as run,
    ):
        service = SubprocessLogcatService()
        assert service.dump("serial-1", 30) == ["one", "two"]
        service.clear_buffer("serial-2")

    assert run.call_args_list[0].args[0] == [
        "C:/adb.exe",
        "-s",
        "serial-1",
        "logcat",
        "-d",
        "-v",
        "threadtime",
        "-t",
        "30",
    ]
    assert run.call_args_list[0].kwargs["timeout"] == 20.0
    assert run.call_args_list[1].args[0] == [
        "C:/adb.exe",
        "-s",
        "serial-2",
        "logcat",
        "-c",
    ]
    assert run.call_args_list[1].kwargs["timeout"] == 10.0


@pytest.mark.parametrize("count", [0, -1, 20001, True])
def test_dump_rejects_count_outside_supported_range(count: int) -> None:
    service = SubprocessLogcatService()

    with pytest.raises(ValueError, match="antara 1 dan 20000"):
        service.dump("serial-1", count)


def test_dump_reports_missing_adb() -> None:
    with patch("super_adb.services.logcat_service.shutil.which", return_value=None):
        with pytest.raises(AdbNotFoundError, match="ADB tidak ditemukan"):
            SubprocessLogcatService().dump("serial-1", 30)


def test_close_stops_all_streams() -> None:
    processes = [BlockingProcess(), BlockingProcess()]
    end_events = [threading.Event(), threading.Event()]
    process_iter = iter(processes)
    created = [threading.Event(), threading.Event()]
    next_process = 0

    def popen(*_args: object, **_kwargs: object) -> BlockingProcess:
        nonlocal next_process
        created[next_process].set()
        next_process += 1
        return next(process_iter)

    with (
        patch("super_adb.services.logcat_service.shutil.which", return_value="adb"),
        patch("super_adb.services.logcat_service.subprocess.Popen", side_effect=popen),
    ):
        service = SubprocessLogcatService()
        for index, serial in enumerate(("serial-1", "serial-2")):
            service.start_stream(
                serial, lambda _: None, lambda *_args, index=index: end_events[index].set()
            )
        assert all(event.wait(timeout=2) for event in created)
        service.close()

    assert all(event.is_set() for event in end_events)
    assert all(process.terminate_calls == 1 for process in processes)
