import tkinter as tk

from super_adb.views.dispatcher import TkDispatcher


class FakeRoot:
    def __init__(self) -> None:
        self.destroyed = False
        self.after_calls = 0

    def after(self, interval_ms: int, callback) -> str:
        self.after_calls += 1
        if self.destroyed:
            raise tk.TclError("application has been destroyed")
        return "poll-id"

    def after_cancel(self, after_id: str) -> None:
        if self.destroyed:
            raise tk.TclError("application has been destroyed")


def test_close_suppresses_tcl_error_when_root_is_already_destroyed() -> None:
    root = FakeRoot()
    dispatcher = TkDispatcher(root)
    root.destroyed = True

    dispatcher.close()

    assert dispatcher._closed is True
    assert root.after_calls == 1


def test_polling_stops_if_root_is_destroyed_before_reschedule() -> None:
    root = FakeRoot()
    dispatcher = TkDispatcher(root)
    root.destroyed = True

    dispatcher._drain()

    assert dispatcher._closed is True
    assert root.after_calls == 2
