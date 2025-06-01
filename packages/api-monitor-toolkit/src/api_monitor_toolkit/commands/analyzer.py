import shlex
import shutil
import subprocess
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
from api_monitor_toolkit.utils.callbacks import verbose_callback
from api_monitor_toolkit.utils.helpers import copy_to_clipboard
from api_monitor_toolkit.utils.logger import get_logger

logger = get_logger(__name__)
app = typer.Typer()


# --- Enums ---
class AttachMode(str, Enum):
    STATIC_IMPORT = "static-import"
    CONTEXT_SWITCH = "context-switch"
    INTERNAL_DEBUGGER = "internal-debugger"
    REMOTE_THREAD_EXTENDED = "remote-thread-extended"
    REMOTE_THREAD_STANDARD = "remote-thread-standard"


# --- Utilidades de Shell / GUI ---
def send_text(shell, text: str):
    copy_to_clipboard(text)
    shell.SendKeys("^v")
    time.sleep(0.3)


def set_foreground(hwnd: int):
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(hwnd)


def open_monitor_dialog(shell):
    time.sleep(5)
    shell.SendKeys("^m")
    time.sleep(1)
    shell.AppActivate("Monitor Process")


def fill_monitor_form(shell, binary: Path, args: list[str], workdir: Path, mode: AttachMode):
    time.sleep(2)
    send_text(shell, str(binary))
    shell.SendKeys("{TAB}")
    send_text(shell, " ".join(shlex.quote(arg) for arg in args))
    shell.SendKeys("{TAB}")
    send_text(shell, str(workdir))
    shell.SendKeys("{TAB}")
    for _ in list(AttachMode):
        shell.SendKeys("{UP}")
    for _ in range(list(AttachMode).index(mode)):
        shell.SendKeys("{DOWN}")
    shell.SendKeys("{ENTER}")


def save_apmx(shell, path: Path):
    shell.SendKeys("^s")
    send_text(shell, str(path))
    shell.SendKeys("{ENTER}")


# --- Funciones principales ---
def detect_arch(binary: Path) -> str:
    pe = pefile.PE(str(binary))
    return "x64" if pe.FILE_HEADER.Machine == 0x8664 else "x86"


def launch_monitor(exe: Path) -> subprocess.Popen:
    return subprocess.Popen([str(exe)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def wait_for_window(filter_fn, timeout: float) -> int:
    end = time.time() + timeout
    while time.time() < end:
        try:
            return find_main_window(filter_fn)
        except MainWindowNotFound:
            time.sleep(0.5)
    raise typer.Exit("API Monitor main window did not appear in time")


def wait_for_process_exit(process_name: str, timeout: float = 60.0):
    logger.info(f"Esperando a que arranque el proceso '{process_name}'...")

    # Esperar a que aparezca
    end_time = time.time() + timeout
    while time.time() < end_time:
        if any(p.name().lower() == process_name.lower() for p in psutil.process_iter()):
            logger.info(f"Proceso '{process_name}' detectado.")
            break
        time.sleep(1)
    else:
        raise typer.Exit(f"Timeout esperando a que arranque '{process_name}'")

    logger.info(f"Esperando a que finalice el proceso '{process_name}'...")

    # Esperar a que desaparezca
    end_time = time.time() + timeout
    while time.time() < end_time:
        if not any(p.name().lower() == process_name.lower() for p in psutil.process_iter()):
            logger.info(f"Proceso '{process_name}' finalizado.")
            return
        time.sleep(1)

    raise typer.Exit(f"Timeout esperando a que finalice '{process_name}'")


def close_monitor(proc: subprocess.Popen):
    for title in ("Monitor Process", "API Monitor"):
        hwnd = win32gui.FindWindow(None, title)
        if hwnd:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
    time.sleep(1)
    if proc.poll() is None:
        proc.kill()


def get_results(dir: Path) -> list[Path]:
    return list(dir.glob("*.apmx*"))


def save_results(results: list[Path], output: str, temp: Path, name: str):
    if not results:
        raise typer.Exit("No .apmx results found")

    zip_path = temp / f"{name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in results:
            zf.write(f, arcname=f.name)

    if output.startswith("http"):
        with open(zip_path, "rb") as f:
            resp = requests.post(output, files={"file": f})
            if resp.status_code != 200:
                raise typer.Exit(f"Upload failed: HTTP {resp.status_code}")
        logger.info(f"Results uploaded to {output}")
        zip_path.unlink(missing_ok=True)
        return

    out_path = Path(output)
    if out_path.suffix.lower() == ".zip":
        shutil.move(str(zip_path), out_path)
        logger.info(f"Results saved to {out_path.resolve()}")
        return

    raise typer.Exit(f"Invalid output: '{output}'. Use .zip or HTTP URL.")


# --- CLI Principal ---
@app.command()
def analyzer(
    input: Annotated[Path, typer.Option("-i", exists=True, help="Path to binary")],
    arguments: Annotated[str, typer.Option("-a", help="Command-line arguments")] = "",
    working_directory: Annotated[Path, typer.Option("-w", help="Working directory")] = Path.cwd(),
    attach_mode: Annotated[AttachMode, typer.Option("-m", help="Attach mode")] = AttachMode.STATIC_IMPORT,
    rohitab_dir: Annotated[Path, typer.Option("-r", help="Rohitab install dir")] = Path(r"C:\Program Files\rohitab.com\API Monitor"),
    window_wait:  Annotated[int, typer.Option("-t", help="Window wait timeout")] = 5,
    output: Annotated[str, typer.Option("-o", help="Output path (.zip or HTTP URL)")] = "results.zip",
    verbosity: Annotated[
        int,
        typer.Option(
            "-v", "--verbose",
            count=True,
            callback=verbose_callback,
            help="Increase output verbosity (use multiple times)"
        )
    ] = 0,
):
    binary = input.resolve()
    workdir = working_directory.resolve()
    args = shlex.split(arguments)
    temp = workdir / f"api_monitor_temp_{binary.stem}"
    shutil.rmtree(temp, ignore_errors=True)
    temp.mkdir(parents=True)

    arch = detect_arch(binary)
    exe = rohitab_dir / f"apimonitor-{arch}.exe"

    proc = launch_monitor(exe)
    hwnd = wait_for_window(lambda title: "API Monitor" in title, window_wait)
    set_foreground(hwnd)

    shell = win32com.client.Dispatch("WScript.Shell")
    open_monitor_dialog(shell)
    fill_monitor_form(shell, binary, args, workdir, attach_mode)

    try:
        wait_for_process_exit(binary.name, timeout=120)
        save_apmx(shell, temp / "terminated")
    except KeyboardInterrupt:
        save_apmx(shell, temp / "interrupted")

    close_monitor(proc)
    results = get_results(temp)
    save_results(results, output, temp, binary.stem)
    shutil.rmtree(temp)
