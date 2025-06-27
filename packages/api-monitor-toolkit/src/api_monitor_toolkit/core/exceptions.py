class MainWindowNotFound(Exception):
    """Raised when the main application window cannot be found."""

    pass


class ChildControlsNotFound(Exception):
    """Raised when no matching child controls are found under a given parent window."""

    pass


class RemoteMemoryAccessError(Exception):
    """Raised when remote memory read/write operations fail."""

    pass


class MonitorProcessTimeout(Exception):
    """Raised when the target process doesn't start or exit within the expected time."""

    pass


class OutputHandlerError(Exception):
    """Raised when output writing fails (e.g., file, HTTP, etc.)."""

    pass
