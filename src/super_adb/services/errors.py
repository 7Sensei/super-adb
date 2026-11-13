class AdbError(Exception):
    """An ADB command failed."""


class AdbNotFoundError(AdbError):
    """The ADB executable could not be found."""


class AdbTimeoutError(AdbError):
    """An ADB command exceeded its time limit."""
