from typing import Callable

import win32gui
from api_monitor_toolkit.core.exceptions import (
    ChildControlsNotFound,
    MainWindowNotFound,
)
from common.logger import get_logger

logger = get_logger(__name__)


def _log_window(hwnd: int, label: str) -> None:
    """Log minimal structured info for a window/control."""
    class_name = win32gui.GetClassName(hwnd)
    title = win32gui.GetWindowText(hwnd)
    logger.debug(f"[{label}] HWND={hwnd}, Class='{class_name}', Title='{title}'")


def _get_children(hwnd_parent: int) -> list[int]:
    """Return all direct children of a window."""
    result = []
    win32gui.EnumChildWindows(hwnd_parent, lambda h, _: result.append(h), None)
    return result


def find_main_window(title_filter: Callable[[str], bool]) -> int:
    """Find the first visible top-level window matching the title filter."""
    matches = []

    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title_filter(title):
                matches.append(hwnd)

    win32gui.EnumWindows(callback, None)

    if not matches:
        raise MainWindowNotFound("No matching main window found.")
    if len(matches) > 1:
        logger.warning(f"Multiple windows matched: {matches}")

    hwnd = matches[0]
    _log_window(hwnd, "MainWindow")
    return hwnd


def find_control(hwnd_parent: int, match: Callable[[int], bool]) -> int:
    """Find first matching child control under a parent."""
    for hwnd in _get_children(hwnd_parent):
        if match(hwnd):
            _log_window(hwnd, "MatchedControl")
            return hwnd
    raise ChildControlsNotFound(f"No control matched under HWND={hwnd_parent}")


def find_controls(hwnd_parent: int, match: Callable[[int], bool]) -> list[int]:
    """Find all matching controls under a parent."""
    results = [hwnd for hwnd in _get_children(hwnd_parent) if match(hwnd)]
    if not results:
        raise ChildControlsNotFound(f"No controls matched under HWND={hwnd_parent}")
    for hwnd in results:
        _log_window(hwnd, "MatchedControl")
    return results
