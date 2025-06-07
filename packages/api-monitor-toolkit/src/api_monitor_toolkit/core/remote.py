import ctypes
import unicodedata
from ctypes import wintypes

import commctrl as cc
import win32api
import win32con as wc
import win32gui
import win32process


class RemoteProcess:
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    def __init__(self, hwnd: int):
        process_id = win32process.GetWindowThreadProcessId(hwnd)[1]
        permissions = wc.PROCESS_VM_OPERATION | wc.PROCESS_VM_READ | wc.PROCESS_VM_WRITE
        self.handle = self._kernel32.OpenProcess(permissions, False, process_id)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())

    def alloc(self, size: int) -> int:
        return self._kernel32.VirtualAllocEx(
            self.handle, 0, size, wc.MEM_RESERVE | wc.MEM_COMMIT, wc.PAGE_READWRITE
        )

    def free(self, address: int):
        self._kernel32.VirtualFreeEx(self.handle, address, 0, wc.MEM_RELEASE)

    def read(self, address: int, size: int) -> bytes:
        buffer = ctypes.create_string_buffer(size)
        self._kernel32.ReadProcessMemory(self.handle, address, buffer, size, None)
        return buffer.raw

    def write(self, address: int, data: bytes | ctypes.Array):
        self._kernel32.WriteProcessMemory(self.handle, address, data, len(data), None)

    def read_utf16z(self, address: int, max_bytes: int) -> str:
        raw = self.read(address, max_bytes)
        text = raw.decode("utf-16le", "ignore")
        return text.split("\x00", 1)[0]

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
    BUFFER_SIZE = 4096
    STRUCT_SIZE = 512

    def __init__(self, header_hwnd: int, listview_hwnd: int):
        self.header = header_hwnd
        self.listview = listview_hwnd
        self.process = RemoteProcess(header_hwnd)
        self.buffer = self.process.alloc(self.BUFFER_SIZE)
        self.temp = self.process.alloc(self.STRUCT_SIZE)

    def get_columns(self) -> list[str]:
        count = win32gui.SendMessage(self.header, cc.HDM_GETITEMCOUNT, 0, 0)
        columns = []
        for i in range(count):
            item = HDITEM()
            item.mask = cc.HDI_TEXT
            item.pszText = ctypes.cast(self.buffer, wintypes.LPWSTR)
            item.cchTextMax = self.BUFFER_SIZE // 2
            self.process.write(
                self.temp, ctypes.string_at(ctypes.byref(item), ctypes.sizeof(item))
            )
            win32gui.SendMessage(self.header, cc.HDM_GETITEMW, i, self.temp)
            columns.append(self.process.read_utf16z(self.buffer, self.BUFFER_SIZE))
        return columns

    def _read_row(self, index: int, num_columns: int) -> list[str]:
        row = []
        for col in range(num_columns):
            item = LVITEM()
            item.mask = cc.LVIF_TEXT
            item.iItem = index
            item.iSubItem = col
            item.pszText = ctypes.cast(self.buffer, wintypes.LPWSTR)
            item.cchTextMax = self.BUFFER_SIZE // 2
            self.process.write(
                self.temp, ctypes.string_at(ctypes.byref(item), ctypes.sizeof(item))
            )
            win32gui.SendMessage(self.listview, cc.LVM_GETITEMTEXTW, index, self.temp)
            row.append(self.process.read_utf16z(self.buffer, self.BUFFER_SIZE))
        return row

    @staticmethod
    def _normalize(text: str) -> str:
        return unicodedata.normalize("NFKC", text).strip().lower()

    def _select_columns(self, headers, desired):
        if desired is None:
            return list(range(len(headers))), headers

        normalized_map = {self._normalize(h): i for i, h in enumerate(headers)}
        indices = [
            normalized_map[self._normalize(h)]
            for h in desired
            if self._normalize(h) in normalized_map
        ]

        if not indices:
            raise KeyError(
                f"None of the requested headers exist.\nAvailable: {headers}"
            )

        selected_headers = [headers[i] for i in indices]
        return indices, selected_headers

    def get_rows(self, desired_columns: list[str] | None = None) -> list[list[str]]:
        headers = self.get_columns()
        indices, _ = self._select_columns(headers, desired_columns)
        total_items = win32gui.SendMessage(self.listview, cc.LVM_GETITEMCOUNT, 0, 0)
        return [
            [self._read_row(i, len(headers))[j] for j in indices]
            for i in range(total_items)
        ]

    def as_json(self, desired_columns: list[str] | None = None) -> list[dict[str, str]]:
        headers = self.get_columns()
        indices, selected_headers = self._select_columns(headers, desired_columns)
        total_items = win32gui.SendMessage(self.listview, cc.LVM_GETITEMCOUNT, 0, 0)

        data = []
        for i in range(total_items):
            row = self._read_row(i, len(headers))
            data.append(
                {header: row[j] for header, j in zip(selected_headers, indices)}
            )
        return data

    def each(self, desired_columns=None, callback=None):
        for index, row in enumerate(self.as_json(desired_columns)):
            if callback:
                callback(row, index)
            yield row

    def select(self, index: int, style: str = "select") -> bool:
        item = LVITEM()
        item.stateMask = item.state = cc.LVIS_SELECTED | cc.LVIS_FOCUSED
        self.process.write(
            self.temp, ctypes.string_at(ctypes.byref(item), ctypes.sizeof(item))
        )
        result = win32gui.SendMessage(
            self.listview, cc.LVM_SETITEMSTATE, index, self.temp
        )

        if result and style == "click":
            win32gui.SendMessage(self.listview, cc.LVM_ENSUREVISIBLE, index, False)
            win32gui.PostMessage(self.listview, wc.WM_LBUTTONDBLCLK, 0, 0)

        return bool(result)

    def close(self):
        self.process.free(self.buffer)
        self.process.free(self.temp)
        self.process.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


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
    BUFFER_SIZE = 4096
    ITEM_SIZE = ctypes.sizeof(TVITEMEX)

    def __init__(self, hwnd: int):
        self.hwnd = hwnd
        self.process = RemoteProcess(hwnd)
        self.buffer = self.process.alloc(self.BUFFER_SIZE)
        self.temp = self.process.alloc(self.ITEM_SIZE)

    def get_root_item(self):
        return win32gui.SendMessage(self.hwnd, cc.TVM_GETNEXTITEM, cc.TVGN_ROOT, 0)

    def get_child_item(self, hitem):
        return win32gui.SendMessage(self.hwnd, cc.TVM_GETNEXTITEM, cc.TVGN_CHILD, hitem)

    def get_next_sibling(self, hitem):
        return win32gui.SendMessage(self.hwnd, cc.TVM_GETNEXTITEM, cc.TVGN_NEXT, hitem)

    def get_item_text(self, hitem):
        item = TVITEMEX()
        item.mask = cc.TVIF_TEXT
        item.hItem = hitem
        item.pszText = ctypes.cast(self.buffer, wintypes.LPWSTR)
        item.cchTextMax = self.BUFFER_SIZE // 2
        self.process.write(
            self.temp, ctypes.string_at(ctypes.byref(item), self.ITEM_SIZE)
        )
        win32gui.SendMessage(self.hwnd, cc.TVM_GETITEMW, 0, self.temp)
        return self.process.read_utf16z(self.buffer, self.BUFFER_SIZE)

    def walk_roots(self):
        hitem = self.get_root_item()
        while hitem:
            text = self.get_item_text(hitem)
            yield text, hitem
            hitem = self.get_next_sibling(hitem)

    def walk_tree(self, hitem=None):
        if hitem is None:
            hitem = self.get_root_item()
        while hitem:
            text = self.get_item_text(hitem)
            yield text, hitem
            child = self.get_child_item(hitem)
            if child:
                yield from self.walk_tree(child)
            hitem = self.get_next_sibling(hitem)

    def close(self):
        self.process.free(self.buffer)
        self.process.free(self.temp)
        self.process.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
