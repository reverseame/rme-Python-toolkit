import time
import win32con
import win32gui
import pyperclip
from pathlib import Path
from api_monitor_toolkit.core.discovery import find_main_window
from common.logger import get_logger

logger = get_logger(__name__)

def send_text(shell, text: str):
    pyperclip.copy(text)
    shell.SendKeys("^v")
    time.sleep(0.3)

def set_foreground(hwnd: int):
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(hwnd)

def wait_for_window(filter_fn, timeout: float = 5) -> int:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            return find_main_window(filter_fn)
        except Exception:
            time.sleep(0.5)
    raise RuntimeError(f"API Monitor window did not appear within {timeout} seconds")

def bring_monitor_to_front():
    try:
        hwnd = wait_for_window(lambda title: "API Monitor" in title)
        set_foreground(hwnd)
        return True
    except Exception:
        logger.warning("API Monitor window not found when attempting to bring to front.")
        return False

def open_monitor_dialog(shell):
    time.sleep(5)
    shell.SendKeys("^m")
    time.sleep(1)
    shell.AppActivate("Monitor Process")

def fill_monitor_form(shell, binary: Path, args: list[str], workdir: Path, mode):
    time.sleep(2)
    send_text(shell, str(binary))
    shell.SendKeys("{TAB}")
    send_text(shell, " ".join(shlex.quote(arg) for arg in args))
    shell.SendKeys("{TAB}")
    send_text(shell, str(workdir))
    shell.SendKeys("{TAB}")
    total_modes = len(type(mode))
    shell.SendKeys("{UP}" * total_modes)
    mode_index = list(type(mode)).index(mode)
    if mode_index > 0:
        shell.SendKeys("{DOWN}" * mode_index)
    shell.SendKeys("{ENTER}")
