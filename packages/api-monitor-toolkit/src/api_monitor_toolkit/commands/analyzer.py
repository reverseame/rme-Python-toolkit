from pathlib import Path
from enum import Enum
import shlex
import shutil
import subprocess
import sys
import time
from typing import Annotated
import zipfile
import typer
import psutil
import requests
import win32com.client

from api_monitor_toolkit.core.monitor import (
    wait_for_window,
    set_foreground,
    open_monitor_dialog,
    fill_monitor_form,
)
from api_monitor_toolkit.core.runner import (
    launch_monitor,
    detect_arch,
    wait_for_process_start,
    wait_for_process_exit_unbounded,
    kill_target_processes,
    close_monitor,
)
from api_monitor_toolkit.utils.trace import (
    save_apmx,
    get_results,
    save_results,
)
from common.callbacks import verbose_callback
from common.logger import get_logger

logger = get_logger(__name__)
app = typer.Typer()


class AttachMode(str, Enum):
    STATIC_IMPORT = "static-import"
    CONTEXT_SWITCH = "context-switch"
    INTERNAL_DEBUGGER = "internal-debugger"
    REMOTE_THREAD_EXTENDED = "remote-thread-extended"
    REMOTE_THREAD_STANDARD = "remote-thread-standard"


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
    ] = Path(r"C:\\Program Files\\rohitab.com\\API Monitor"),
    timeout: Annotated[
        int,
        typer.Option("-t", "--timeout", help="Seconds to wait for window & process start"),
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

    temp = workdir / f"api_monitor_temp_{binary.stem}"
    shutil.rmtree(temp, ignore_errors=True)
    temp.mkdir(parents=True, exist_ok=True)

    arch = detect_arch(binary)
    exe = rohitab_dir / f"apimonitor-{arch}.exe"

    proc = launch_monitor(exe)

    shell = None
    try:
        hwnd = wait_for_window(lambda t: "API Monitor" in t, timeout)
        set_foreground(hwnd)
        shell = win32com.client.Dispatch("WScript.Shell")
        open_monitor_dialog(shell)
        fill_monitor_form(shell, binary, args, workdir, attach_mode)

        wait_for_process_start(binary.name, timeout)
        wait_for_process_exit_unbounded(binary.name)
        save_apmx(shell, temp / "terminated", timeout)

    except KeyboardInterrupt:
        logger.error("Received Ctrl+C: saving partial trace")
        if shell:
            save_apmx(shell, temp / "interrupted", timeout)

    finally:
        close_monitor(proc)
        kill_target_processes(binary.name)
        results = get_results(temp)
        save_results(results, output, temp, binary.stem)
        shutil.rmtree(temp, ignore_errors=True)

    logger.info("Analysis complete and cleanup done.")
