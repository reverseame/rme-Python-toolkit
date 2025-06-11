import ctypes
import unicodedata
from ctypes import wintypes

import commctrl as cc
import win32api
import win32con as wc
import win32gui
import win32process
from api_monitor_toolkit.core.exceptions import RemoteMemoryAccessError
from common.logger import get_logger

logger = get_logger(__name__)


class RemoteProcess:
    """Provides safe access to memory of another process."""

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    def __init__(self, hwnd: int):
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        perms = wc.PROCESS_VM_READ | wc.PROCESS_VM_WRITE | wc.PROCESS_VM_OPERATION
        handle = self._kernel32.OpenProcess(perms, False, pid)
        if not handle:
            raise RemoteMemoryAccessError("Cannot open target process")
        self.handle = handle

    def alloc(self, size: int) -> int:
        addr = self._kernel32.VirtualAllocEx(
            self.handle, 0, size, wc.MEM_COMMIT | wc.MEM_RESERVE, wc.PAGE_READWRITE
        )
        if not addr:
            raise RemoteMemoryAccessError("Memory allocation failed")
        return addr

    def free(self, addr: int):
        self._kernel32.VirtualFreeEx(self.handle, addr, 0, wc.MEM_RELEASE)

    def read(self, addr: int, size: int) -> bytes:
        buffer = ctypes.create_string_buffer(size)
        success = self._kernel32.ReadProcessMemory(
            self.handle, addr, buffer, size, None
        )
        if not success:
            raise RemoteMemoryAccessError(f"Failed to read memory at {hex(addr)}")
        return buffer.raw

    def write(self, addr: int, data: bytes):
        success = self._kernel32.WriteProcessMemory(
            self.handle, addr, data, len(data), None
        )
        if not success:
            raise RemoteMemoryAccessError(f"Failed to write memory at {hex(addr)}")

    def read_utf16z(self, addr: int, max_bytes: int) -> str:
        raw = self.read(addr, max_bytes)
        return raw.decode("utf-16le", "ignore").split("\x00", 1)[0]

    def close(self):
        win32api.CloseHandle(self.handle)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


class HDITEM(ctypes.Structure):
    _fields_ = [
        ("mask", wintypes.UINT),
        ("cxy", wintypes.INT),
        ("pszText", wintypes.LPWSTR),
        ("hbm", wintypes.HBITMAP),
        ("cchTextMax", wintypes.INT),
        ("fmt", wintypes.INT),
        ("lParam", wintypes.LPARAM),
    ]


class LVITEM(ctypes.Structure):
    _fields_ = [
        ("mask", wintypes.UINT),
        ("iItem", wintypes.INT),
        ("iSubItem", wintypes.INT),
        ("state", wintypes.UINT),
        ("stateMask", wintypes.UINT),
        ("pszText", wintypes.LPWSTR),
        ("cchTextMax", wintypes.INT),
        ("iImage", wintypes.INT),
        ("lParam", wintypes.LPARAM),
    ]


class RemoteListView:
    """Represents a remote ListView control and supports row/column access."""

    BUF_SIZE = 4096
    ITEM_SIZE = ctypes.sizeof(LVITEM)

    def __init__(self, header_hwnd: int, list_hwnd: int):
        self.header = header_hwnd
        self.list = list_hwnd
        self.proc = RemoteProcess(header_hwnd)
        self.buf = self.proc.alloc(self.BUF_SIZE)
        self.temp = self.proc.alloc(self.ITEM_SIZE)

    def close(self):
        self.proc.free(self.buf)
        self.proc.free(self.temp)
        self.proc.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def get_columns(self) -> list[str]:
        count = win32gui.SendMessage(self.header, cc.HDM_GETITEMCOUNT, 0, 0)
        columns = []
        for i in range(count):
            item = HDITEM()
            item.mask = cc.HDI_TEXT
            item.pszText = ctypes.cast(self.buf, wintypes.LPWSTR)
            item.cchTextMax = self.BUF_SIZE // 2
            self.proc.write(
                self.temp, ctypes.string_at(ctypes.byref(item), ctypes.sizeof(item))
            )
            win32gui.SendMessage(self.header, cc.HDM_GETITEMW, i, self.temp)
            columns.append(self.proc.read_utf16z(self.buf, self.BUF_SIZE))
        return columns

    def _read_row(self, index: int, num_columns: int) -> list[str]:
        row = []
        for col in range(num_columns):
            item = LVITEM()
            item.mask = cc.LVIF_TEXT
            item.iItem = index
            item.iSubItem = col
            item.pszText = ctypes.cast(self.buf, wintypes.LPWSTR)
            item.cchTextMax = self.BUF_SIZE // 2
            self.proc.write(
                self.temp, ctypes.string_at(ctypes.byref(item), self.ITEM_SIZE)
            )
            win32gui.SendMessage(self.list, cc.LVM_GETITEMTEXTW, index, self.temp)
            row.append(self.proc.read_utf16z(self.buf, self.BUF_SIZE))
        return row

    def _normalize(self, text: str) -> str:
        return unicodedata.normalize("NFKC", text).strip().lower()

    def _select_columns(self, headers, desired):
        if desired is None:
            return list(range(len(headers))), headers
        norm_map = {self._normalize(h): i for i, h in enumerate(headers)}
        indices = [
            norm_map[self._normalize(h)]
            for h in desired
            if self._normalize(h) in norm_map
        ]
        selected = [headers[i] for i in indices]
        return indices, selected

    def get_rows(self, desired_columns=None) -> list[list[str]]:
        headers = self.get_columns()
        indices, _ = self._select_columns(headers, desired_columns)
        total = win32gui.SendMessage(self.list, cc.LVM_GETITEMCOUNT, 0, 0)
        return [
            [self._read_row(i, len(headers))[j] for j in indices] for i in range(total)
        ]

    def as_json(self, desired_columns=None) -> list[dict[str, str]]:
        headers = self.get_columns()
        indices, keys = self._select_columns(headers, desired_columns)
        total = win32gui.SendMessage(self.list, cc.LVM_GETITEMCOUNT, 0, 0)
        result = []
        for i in range(total):
            row = self._read_row(i, len(headers))
            result.append({key: row[j] for key, j in zip(keys, indices)})
        return result

    def select(self, index: int) -> bool:
        item = LVITEM()
        item.stateMask = item.state = cc.LVIS_SELECTED | cc.LVIS_FOCUSED
        self.proc.write(self.temp, ctypes.string_at(ctypes.byref(item), self.ITEM_SIZE))
        return bool(
            win32gui.SendMessage(self.list, cc.LVM_SETITEMSTATE, index, self.temp)
        )


class TVITEMEX(ctypes.Structure):
    _fields_ = [
        ("mask", wintypes.UINT),
        ("hItem", wintypes.HANDLE),
        ("state", wintypes.UINT),
        ("stateMask", wintypes.UINT),
        ("pszText", wintypes.LPWSTR),
        ("cchTextMax", wintypes.INT),
        ("iImage", wintypes.INT),
        ("iSelectedImage", wintypes.INT),
        ("cChildren", wintypes.INT),
        ("lParam", wintypes.LPARAM),
        ("iIntegral", wintypes.INT),
        ("uStateEx", wintypes.UINT),
        ("hwnd", wintypes.HWND),
        ("iExpandedImage", wintypes.INT),
        ("iReserved", wintypes.INT),
    ]


class RemoteTreeView:
    """Represents a remote TreeView and supports traversal."""

    BUF_SIZE = 4096
    ITEM_SIZE = ctypes.sizeof(TVITEMEX)

    def __init__(self, hwnd: int):
        self.hwnd = hwnd
        self.proc = RemoteProcess(hwnd)
        self.buf = self.proc.alloc(self.BUF_SIZE)
        self.temp = self.proc.alloc(self.ITEM_SIZE)

    def close(self):
        self.proc.free(self.buf)
        self.proc.free(self.temp)
        self.proc.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _get_text(self, hitem):
        item = TVITEMEX()
        item.mask = cc.TVIF_TEXT
        item.hItem = hitem
        item.pszText = ctypes.cast(self.buf, wintypes.LPWSTR)
        item.cchTextMax = self.BUF_SIZE // 2
        self.proc.write(self.temp, ctypes.string_at(ctypes.byref(item), self.ITEM_SIZE))
        win32gui.SendMessage(self.hwnd, cc.TVM_GETITEMW, 0, self.temp)
        return self.proc.read_utf16z(self.buf, self.BUF_SIZE)

    def _get_next(self, hitem, flag):
        return win32gui.SendMessage(self.hwnd, cc.TVM_GETNEXTITEM, flag, hitem)

    def walk_roots(self):
        item = self._get_next(0, cc.TVGN_ROOT)
        while item:
            yield self._get_text(item), item
            item = self._get_next(item, cc.TVGN_NEXT)
