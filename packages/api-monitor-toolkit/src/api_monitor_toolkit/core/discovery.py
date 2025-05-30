from typing import Callable

import win32gui
from api_monitor_toolkit.core.exceptions import (
    ChildControlsNotFound,
    MainWindowNotFound,
)
from api_monitor_toolkit.utils.logger import get_logger

logger = get_logger(__name__)


def _log_window_info(
    hwnd: int,
    label: str,
    *,
    show_title: bool = True,
    show_rect: bool = True,
    show_visibility: bool = True,
):
    """Logs detailed info about a window/control in a structured format."""
    class_name = win32gui.GetClassName(hwnd)
    title = win32gui.GetWindowText(hwnd)
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width, height = right - left, bottom - top
    visible = win32gui.IsWindowVisible(hwnd)
    enabled = win32gui.IsWindowEnabled(hwnd)

    lines = [
        f"[{label}]",
        f"HWND    : {hwnd}",
        f"Class   : {class_name}",
        f"Title   : {title}" if show_title else None,
        f"Rect    : ({left}, {top}) - ({right}, {bottom})  [Width={width}, Height={height}]" if show_rect else None,
        f"Visible : {int(visible)}" if show_visibility else None,
        f"Enabled : {int(enabled)}" if show_visibility else None,
    ]

    logger.debug("\n".join(line for line in lines if line is not None))


def _get_child_windows(hwnd: int) -> list[int]:
    """Returns all direct child HWNDs for a given parent window."""
    result = []
    win32gui.EnumChildWindows(hwnd, lambda h, _: result.append(h), None)
    return result


def find_main_window(title_filter: Callable[[str], bool]) -> int:
    """Finds the main window matching the given title filter."""
    matches = []

    def enum_callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title_filter(title):
                matches.append(hwnd)

    win32gui.EnumWindows(enum_callback, None)

    if not matches:
        raise MainWindowNotFound("No matching main window found.")

    if len(matches) > 1:
        logger.warning(f"Multiple matching windows found: {matches}")

    hwnd = matches[0]
    _log_window_info(hwnd, label="Main Window", show_rect=False, show_visibility=False)
    logger.info(f"Main window found: '{win32gui.GetWindowText(hwnd)}' (HWND={hwnd})")
    return hwnd


def find_child_windows(hwnd_parent: int, filter_callback: Callable[[int], bool]) -> list[int]:
    """Returns all child HWNDs under the given parent that match the filter."""
    result = []

    for hwnd in _get_child_windows(hwnd_parent):
        if filter_callback(hwnd):
            _log_window_info(hwnd, label="Child Window", show_rect=False, show_visibility=False)
            result.append(hwnd)

    logger.info(f"{len(result)} matching child window(s) found under parent HWND={hwnd_parent}")
    return result


def find_child_controls(hwnd_parent: int, filter_callback: Callable[[int], bool]) -> list[int]:
    """Returns all matching control HWNDs under the given parent (e.g., ListView, TreeView)."""
    matched_hwnds = []

    for hwnd in _get_child_windows(hwnd_parent):
        if filter_callback(hwnd):
            _log_window_info(hwnd, label="Control", show_title=False, show_rect=False, show_visibility=False)
            matched_hwnds.append(hwnd)

    if not matched_hwnds:
        raise ChildControlsNotFound(f"No matching controls found under HWND={hwnd_parent}.")

    logger.info(f"{len(matched_hwnds)} control(s) found in parent window (HWND={hwnd_parent})")
    return matched_hwnds


def find_control(hwnd_parent: int, filter_callback: Callable[[int], bool]) -> int:
    """
    Finds and returns the first control under the given parent that matches the filter.
    Raises ChildControlsNotFound if none is found.
    """
    for hwnd in _get_child_windows(hwnd_parent):
        if filter_callback(hwnd):
            _log_window_info(hwnd, label="Matched Control", show_title=False, show_rect=False, show_visibility=False)
            logger.info(f"Control found (HWND={hwnd}) under parent (HWND={hwnd_parent})")
            return hwnd

    raise ChildControlsNotFound(f"No matching control found under HWND={hwnd_parent}.")
