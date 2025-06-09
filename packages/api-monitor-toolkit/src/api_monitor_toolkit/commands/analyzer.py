import shlex
import shutil
import subprocess
import sys
import time
import zipfile
from enum import Enum
from pathlib import Path
from typing import Annotated

import pefile
import psutil
import requests
import typer
import win32com.client
import win32con
import win32gui
from api_monitor_toolkit.core.discovery import MainWindowNotFound, find_main_window
from common.callbacks import verbose_callback
from api_monitor_toolkit.utils.helpers import copy_to_clipboard
from common.logger import get_logger

logger = get_logger(__name__)
app = typer.Typer()


class AttachMode(str, Enum):
    """
    Different methods to attach API Monitor to the target process.
    """

    STATIC_IMPORT = "static-import"
    CONTEXT_SWITCH = "context-switch"
    INTERNAL_DEBUGGER = "internal-debugger"
    REMOTE_THREAD_EXTENDED = "remote-thread-extended"
    REMOTE_THREAD_STANDARD = "remote-thread-standard"


def send_text(shell, text: str):
    """
    Copy text to clipboard and paste it into the active window.
    """
    copy_to_clipboard(text)
    shell.SendKeys("^v")
    time.sleep(0.3)


def set_foreground(hwnd: int):
    """
    Restore and bring the specified window handle to the foreground.
    """
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(hwnd)


def bring_monitor_to_front():
    """
    Find the 'Monitor Process' dialog or 'API Monitor' main window
    and bring it to the foreground, if it exists.
    """
    hwnd = wait_for_window(lambda title: "API Monitor" in title)
    if hwnd:
        set_foreground(hwnd)
        return True
    return False


def open_monitor_dialog(shell):
    """
    Wait a moment and send Ctrl+M to open the 'Monitor Process' dialog in API Monitor.
    """
    time.sleep(5)
    shell.SendKeys("^m")
    time.sleep(1)
    shell.AppActivate("Monitor Process")


def fill_monitor_form(
    shell, binary: Path, args: list[str], workdir: Path, mode: AttachMode
):
    """
    Populate the 'Monitor Process' dialog fields: binary path, arguments, working directory, and attach mode.
    """
    time.sleep(2)
    # Binary path
    send_text(shell, str(binary))
    shell.SendKeys("{TAB}")

    # Command-line arguments
    send_text(shell, " ".join(shlex.quote(arg) for arg in args))
    shell.SendKeys("{TAB}")

    # Working directory
    send_text(shell, str(workdir))
    shell.SendKeys("{TAB}")

    # Reset attach-mode dropdown to first entry
    total_modes = len(AttachMode)
    shell.SendKeys("{UP}" * total_modes)

    # Move down to selected attach mode
    mode_index = list(AttachMode).index(mode)
    if mode_index > 0:
        shell.SendKeys("{DOWN}" * mode_index)

    # Confirm selection
    shell.SendKeys("{ENTER}")


def save_apmx(shell, path: Path, timeout: int):
    """
    Send Ctrl+S, type the target save path, and press Enter to save the .apmx trace.
    """
    if not bring_monitor_to_front():
        logger.warning("API Monitor window not found when attempting to save .apmx.")
    shell.SendKeys("^s")
    time.sleep(0.2)
    send_text(shell, str(path))
    shell.SendKeys("{ENTER}")
    time.sleep(timeout)


def detect_arch(binary: Path) -> str:
    """
    Inspect the PE header of the target binary to determine whether it's x86 or x64.
    """
    pe = pefile.PE(str(binary))
    return "x64" if pe.FILE_HEADER.Machine == 0x8664 else "x86"


def launch_monitor(exe: Path) -> subprocess.Popen:
    """
    Launch API Monitor (suppressing its stdout/stderr).
    """
    return subprocess.Popen(
        [str(exe)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def wait_for_window(filter_fn, timeout: float = 5) -> int:
    """
    Poll until API Monitor's main window appears or timeout is reached.
    Returns the window handle. Raises RuntimeError on timeout.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            return find_main_window(filter_fn)
        except MainWindowNotFound:
            time.sleep(0.5)
    raise RuntimeError(f"API Monitor window did not appear within {timeout} seconds")


def wait_for_process_start(process_name: str, timeout: float):
    """
    Wait until a process with the given name appears, or raise RuntimeError on timeout.
    """
    logger.info(f"Waiting up to {timeout}s for process '{process_name}' to start...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        if any(p.name().lower() == process_name.lower() for p in psutil.process_iter()):
            logger.info(f"Process '{process_name}' detected.")
            return
        time.sleep(1)
    raise RuntimeError(f"Timeout waiting for '{process_name}' to start")


def wait_for_process_exit_unbounded(process_name: str):
    """
    Wait indefinitely until the process with the given name exits.
    """
    logger.info(f"Waiting for process '{process_name}' to exit...")
    while True:
        if not any(
            p.name().lower() == process_name.lower() for p in psutil.process_iter()
        ):
            logger.info(f"Process '{process_name}' has exited.")
            return
        time.sleep(1)


def close_monitor(proc: subprocess.Popen):
    """
    Attempt to close API Monitor gracefully by sending WM_CLOSE to its windows;
    if it is still running, kill the process.
    """
    for title in ("Monitor Process", "API Monitor"):
        hwnd = win32gui.FindWindow(None, title)
        if hwnd:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
    time.sleep(1)
    if proc.poll() is None:
        proc.kill()


def kill_target_processes(process_name: str):
    """
    Terminate any processes matching the given name.
    """
    for p in psutil.process_iter():
        if p.name().lower() == process_name.lower():
            try:
                p.kill()
                logger.info(f"Killed target process '{process_name}' (PID {p.pid}).")
            except Exception:
                pass


def get_results(temp_dir: Path) -> list[Path]:
    """
    Return a list of all .apmx and .apmx* files found in the temporary directory.
    """
    return list(temp_dir.glob("*.apmx*"))


def save_results(results: list[Path], output: str, temp: Path, base_name: str):
    """
    Zip up any .apmx files and either move the .zip to a local path or upload via HTTP.

    - If output starts with 'http', POST the zip as 'file' to that URL.
    - If output ends with '.zip', move the temp zip to that path.
    - Otherwise log an error and exit.
    """
    if not results:
        logger.warning("No .apmx files found to save")
    zip_path = temp / f"{base_name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in results:
            zf.write(f, arcname=f.name)

    if output.lower().startswith("http"):
        with open(zip_path, "rb") as f:
            resp = requests.post(output, files={"file": f})
            if resp.status_code != 200:
                logger.error(f"Upload failed: HTTP {resp.status_code}")
                sys.exit(1)
        logger.info(f"Results uploaded to {output}")
        zip_path.unlink(missing_ok=True)
        return

    out_path = Path(output)
    if out_path.suffix.lower() == ".zip":
        shutil.move(str(zip_path), out_path)
        logger.info(f"Results saved to {out_path.resolve()}")
        return

    logger.error(f"Invalid output path '{output}'. Must be a .zip or an HTTP URL.")
    sys.exit(1)


@app.command()
def analyzer(
    input: Annotated[
        Path,
        typer.Option("-i", "--input", exists=True, help="Path to the target binary"),
    ],
    arguments: Annotated[
        str, typer.Option("-a", "--args", help="Command-line arguments for the target")
    ] = "",
    working_directory: Annotated[
        Path, typer.Option("-w", "--workdir", help="Working directory")
    ] = Path.cwd(),
    attach_mode: Annotated[
        AttachMode, typer.Option("-m", "--mode", help="Attach mode")
    ] = AttachMode.STATIC_IMPORT,
    rohitab_dir: Annotated[
        Path, typer.Option("-r", "--rohitab", help="API Monitor install directory")
    ] = Path(r"C:\Program Files\rohitab.com\API Monitor"),
    timeout: Annotated[
        int,
        typer.Option(
            "-t", "--timeout", help="Seconds to wait for window & process start"
        ),
    ] = 5,
    output: Annotated[
        str, typer.Option("-o", "--output", help="Output path (.zip or HTTP URL)")
    ] = "results.zip",
    verbosity: Annotated[
        int,
        typer.Option(
            "-v",
            "--verbose",
            count=True,
            callback=verbose_callback,
            help="Increase logging verbosity",
        ),
    ] = 0,
):
    """
    Launch API Monitor, attach to a binary, wait for it to start (with timeout), then wait until it exits.
    If the user presses Ctrl+C at any point, save any partial trace, close API Monitor, kill the target,
    and still zip whatever files exist before exiting.
    """
    binary = input.resolve()
    workdir = working_directory.resolve()
    args = shlex.split(arguments)

    # Prepare temporary directory for .apmx files
    temp = workdir / f"api_monitor_temp_{binary.stem}"
    shutil.rmtree(temp, ignore_errors=True)
    temp.mkdir(parents=True, exist_ok=True)

    # Determine CPU architecture of the target
    arch = detect_arch(binary)
    exe = rohitab_dir / f"apimonitor-{arch}.exe"

    # Launch API Monitor
    proc = launch_monitor(exe)

    # Initialize shell to None; will be set once WScript.Shell is created
    shell = None
    try:
        # Wait for API Monitor main window and bring to front
        hwnd = wait_for_window(lambda title: "API Monitor" in title, timeout)
        set_foreground(hwnd)

        # Prepare WScript.Shell for SendKeys
        shell = win32com.client.Dispatch("WScript.Shell")

        # Open the "Monitor Process" dialog and fill it
        open_monitor_dialog(shell)
        fill_monitor_form(shell, binary, args, workdir, attach_mode)

        # Wait for the target process to start (with timeout)
        wait_for_process_start(binary.name, timeout)

        # Wait indefinitely until the target process exits
        wait_for_process_exit_unbounded(binary.name)

        # Save the trace once the process has exited normally
        save_apmx(shell, temp / "terminated", timeout)
    except KeyboardInterrupt:
        logger.error("Received Ctrl+C: attempting to save partial trace and exit.")
        if shell:
            save_apmx(shell, temp / "interrupted", timeout)
    finally:
        close_monitor(proc)
        kill_target_processes(binary.name)
        results = get_results(temp)
        save_results(results, output, temp, binary.stem)
        shutil.rmtree(temp, ignore_errors=True)

    logger.info("Analysis complete and cleanup done.")
