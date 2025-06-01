import ctypes
from ctypes import wintypes
from typing import Any, Callable

import win32gui
from api_monitor_toolkit.core.discovery import find_child_windows, find_control
from api_monitor_toolkit.core.remote import RemoteListView
from api_monitor_toolkit.utils.logger import get_logger

logger = get_logger(__name__)


class ValueTransformer:
    def __init__(self):
        self.per_key_rules: dict[str, Callable[[str], Any]] = {}

        # Register key-specific rules
        self.register("id", self._to_int)
        self.register("tid", self._to_int)
        self.register("thread", self._to_int)
        self.register("duration", self._to_float)

    def register(self, key: str, fn: Callable[[str], Any]):
        self.per_key_rules[key] = fn

    def transform(self, key: str, value: Any) -> Any:
        if value is None:
            value = ""

        if isinstance(value, str):
            val_str = value.strip()
        else:
            val_str = value

        # Apply per-key rules first
        if key in self.per_key_rules and isinstance(val_str, str):
            try:
                val_str = self.per_key_rules[key](val_str)
            except Exception:
                pass  # fallback to original value

        # Apply general transformations
        if isinstance(val_str, str):
            low = val_str.lower()
            if low == "null":
                return None
            if low == "true":
                return True
            if low == "false":
                return False
            if val_str == "":
                return "undefined"

        return val_str

    def _to_int(self, val: str) -> Any:
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0

    def _to_float(self, val: str) -> Any:
        try:
            return float(val)
        except (ValueError, TypeError):
            return val


def get_mapped_data(
    main_window,
    title_filter: str,
    mapping: dict,
    transformer: ValueTransformer,
    skip_penultimate_empty=False
) -> list[dict[str, Any]]:
    try:
        window = find_child_windows(main_window, lambda hwnd: title_filter in win32gui.GetWindowText(hwnd))[0]
        header = find_control(window, lambda hwnd: win32gui.GetClassName(hwnd) == "SysHeader32")
        listview = find_control(window, lambda hwnd: win32gui.GetClassName(hwnd) == "SysListView32")
        with RemoteListView(header, listview) as view:
            data = view.as_json()
            if skip_penultimate_empty:
                data = [
                    {
                        (mapped := mapping.get(k, k)): transformer.transform(mapped, v)
                        for k, v in row.items()
                    }
                    for i, row in enumerate(data)
                    if i != len(data) - 2 or any(v.strip() for v in row.values())
                ]
            else:
                data = [
                    {
                        (mapped := mapping.get(k, k)): transformer.transform(mapped, v)
                        for k, v in row.items()
                    }
                    for row in data
                ]
            return data
    except Exception as e:
        logger.warning(f"Failed to extract data from '{title_filter}': {e}")
        return []

def copy_to_clipboard(text: str) -> None:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    GMEM_DDESHARE = 0x2000
    CF_UNICODETEXT = 13

    user32.OpenClipboard(0)
    user32.EmptyClipboard()

    size = (len(text) + 1) * ctypes.sizeof(wintypes.WCHAR)
    h_mem = kernel32.GlobalAlloc(GMEM_DDESHARE, size)
    ptr = kernel32.GlobalLock(h_mem)

    ctypes.memmove(ptr, ctypes.create_unicode_buffer(text), size)

    kernel32.GlobalUnlock(h_mem)
    user32.SetClipboardData(CF_UNICODETEXT, h_mem)
    user32.CloseClipboard()
