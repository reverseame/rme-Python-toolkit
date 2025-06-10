import subprocess
import time
import pefile
import psutil
import win32gui
import win32con
from pathlib import Path
from api_monitor_toolkit.core.discovery import find_main_window, MainWindowNotFound
from common.logger import get_logger

logger = get_logger(__name__)

def detect_arch(binary: Path) -> str:
    pe = pefile.PE(str(binary))
    return "x64" if pe.FILE_HEADER.Machine == 0x8664 else "x86"

def launch_monitor(exe: Path) -> subprocess.Popen:
    return subprocess.Popen(
        [str(exe)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

def wait_for_process_start(process_name: str, timeout: float):
    logger.info(f"Waiting up to {timeout}s for process '{process_name}' to start...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        if any(p.name().lower() == process_name.lower() for p in psutil.process_iter()):
            logger.info(f"Process '{process_name}' detected.")
            return
        time.sleep(1)
    raise RuntimeError(f"Timeout waiting for '{process_name}' to start")

def wait_for_process_exit_unbounded(process_name: str):
    logger.info(f"Waiting for process '{process_name}' to exit...")
    while True:
        if not any(p.name().lower() == process_name.lower() for p in psutil.process_iter()):
            logger.info(f"Process '{process_name}' has exited.")
            return
        time.sleep(1)

def close_monitor(proc: subprocess.Popen):
    for title in ("Monitor Process", "API Monitor"):
        hwnd = win32gui.FindWindow(None, title)
        if hwnd:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
    time.sleep(1)
    if proc.poll() is None:
        proc.kill()

def kill_target_processes(process_name: str):
    for p in psutil.process_iter():
        if p.name().lower() == process_name.lower():
            try:
                p.kill()
                logger.info(f"Killed target process '{process_name}' (PID {p.pid}).")
            except Exception:
                pass
