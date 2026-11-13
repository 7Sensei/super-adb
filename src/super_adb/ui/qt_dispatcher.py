import threading
from collections.abc import Callable

from PySide6.QtCore import QObject, Qt, Signal, Slot


class QtDispatcher(QObject):
    _dispatch_requested = Signal(object, object)

    def __init__(self) -> None:
        super().__init__()
        self._state_lock = threading.Lock()
        self._closed = False
        self._dispatch_requested.connect(
            self._deliver,
            Qt.ConnectionType.QueuedConnection,
        )

    def post(self, callback: Callable[[], None]) -> None:
        with self._state_lock:
            if not self._closed:
                self._dispatch_requested.emit(callback, None)

    def close(self) -> None:
        with self._state_lock:
            if self._closed:
                return
            self._closed = True
            self._dispatch_requested.disconnect(self._deliver)

    @Slot(object, object)
    def _deliver(self, callback: Callable[[], None], payload: object) -> None:
        with self._state_lock:
            if self._closed:
                return
        callback()
