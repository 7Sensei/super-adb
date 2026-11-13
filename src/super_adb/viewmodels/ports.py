from collections.abc import Callable
from typing import Protocol


class UiDispatcher(Protocol):
    def post(self, callback: Callable[[], None]) -> None:
        """Schedule a callback on the UI thread."""
