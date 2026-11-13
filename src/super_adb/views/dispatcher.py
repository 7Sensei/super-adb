from __future__ import annotations

import queue
import tkinter as tk
from collections.abc import Callable


class TkDispatcher:
    def __init__(self, root: tk.Misc, interval_ms: int = 50, max_items: int = 200) -> None:
        self._root = root
        self._interval_ms = interval_ms
        self._max_items = max_items
        self._queue: queue.SimpleQueue[Callable[[], None]] = queue.SimpleQueue()
        self._closed = False
        self._after_id: str | None = self._root.after(self._interval_ms, self._drain)

    def post(self, callback: Callable[[], None]) -> None:
        self._queue.put(callback)

    def close(self) -> None:
        self._closed = True
        if self._after_id is not None:
            try:
                self._root.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None

    def _drain(self) -> None:
        try:
            for _ in range(self._max_items):
                try:
                    callback = self._queue.get_nowait()
                except queue.Empty:
                    break
                callback()
        finally:
            if not self._closed:
                try:
                    self._after_id = self._root.after(self._interval_ms, self._drain)
                except tk.TclError:
                    self._closed = True
                    self._after_id = None
