import ctypes
from ctypes import wintypes

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