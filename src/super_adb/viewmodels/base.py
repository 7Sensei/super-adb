from collections.abc import Callable
from typing import Generic, TypeVar

T = TypeVar("T")


class Observable(Generic[T]):
    def __init__(self, value: T) -> None:
        self._value = value
        self._subscribers: list[Callable[[T], None]] = []

    @property
    def value(self) -> T:
        return self._value

    @value.setter
    def value(self, new_value: T) -> None:
        if new_value == self._value:
            return
        self._value = new_value
        for callback in tuple(self._subscribers):
            callback(new_value)

    def subscribe(self, callback: Callable[[T], None]) -> Callable[[], None]:
        self._subscribers.append(callback)

        def unsubscribe() -> None:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

        return unsubscribe


class Signal(Generic[T]):
    def __init__(self) -> None:
        self._subscribers: list[Callable[[T], None]] = []

    def connect(self, callback: Callable[[T], None]) -> Callable[[], None]:
        self._subscribers.append(callback)

        def disconnect() -> None:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

        return disconnect

    def emit(self, payload: T) -> None:
        for callback in tuple(self._subscribers):
            callback(payload)
