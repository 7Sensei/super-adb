class AdbError(Exception):
    """An ADB command failed."""


class AdbNotFoundError(AdbError):
    """The ADB executable could not be found."""
