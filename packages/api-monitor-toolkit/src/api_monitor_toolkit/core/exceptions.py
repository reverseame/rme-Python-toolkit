class MainWindowNotFound(Exception):
    """Raised when the main application window cannot be found."""
    pass


class ChildControlsNotFound(Exception):
    """Raised when no matching child controls are found under a given parent."""
    pass
