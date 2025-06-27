import time
from pathlib import Path
from typing import Annotated

import typer
import win32com.client
from api_monitor_toolkit.core.monitor import send_text, set_foreground, wait_for_window
from api_monitor_toolkit.core.runner import close_monitor, launch_monitor
from api_monitor_toolkit.output.handler import get_output_handler
from api_monitor_toolkit.services.spider_controller import SpiderController
from common.callbacks import verbose_callback
from common.checks import check_python, is_admin
from common.logger import get_logger

logger = get_logger(__name__)
app = typer.Typer()


def detect_apmx_arch(apmx_path: Path) -> str:
    """
    Detect architecture from .apmx file extension.
    Only accepts .apmx64 or .apmx86 extensions.
    """
    suffix = apmx_path.suffix.lower()
    if suffix == ".apmx64":
        return "x64"
    elif suffix == ".apmx86":
        return "x86"
    else:
        logger.error(
            f"Unsupported trace file extension '{suffix}'. Must be .apmx64 or .apmx86."
        )
        raise typer.Exit(code=1)


def load_apmx(shell, apmx_path: Path, timeout=2.5):
    time.sleep(timeout)
    shell.SendKeys("^o")  # Ctrl+O to open APMX file
    time.sleep(1)
    send_text(shell, str(apmx_path))
    shell.SendKeys("{ENTER}")
    time.sleep(timeout)


@app.command()
def spider(
    input: Annotated[
        Path, typer.Option("-i", "--input", exists=True, help="Path to the apmx file")
    ] = None,
    parameters: Annotated[bool, typer.Option("-p", "--parameters")] = False,
    call_stack: Annotated[bool, typer.Option("-c", "--call-stack")] = False,
    output: Annotated[str, typer.Option("-o", "--output")] = None,
    rohitab_dir: Annotated[
        Path, typer.Option("-r", "--rohitab", help="API Monitor install directory")
    ] = Path(r"C:\\Program Files\\rohitab.com\\API Monitor"),
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
    Extract information from API Monitor's UI tree view (previously captured trace).
    If --input is provided, API Monitor will be launched and the trace will be loaded.
    If not, it assumes API Monitor is already open with the trace loaded.
    """
    if not is_admin():
        logger.error("This script must be run as administrator when using --input.")
        raise typer.Exit(code=1)
    check_python()

    try:
        handler = get_output_handler(output)
        proc = None
        if input:
            arch = detect_apmx_arch(input)
            logger.info("Launching API Monitor and loading APMX file...")
            exe = rohitab_dir / f"apimonitor-{arch}.exe"
            proc = launch_monitor(exe)

            hwnd = wait_for_window(lambda title: "API Monitor" in title)
            set_foreground(hwnd)
            shell = win32com.client.Dispatch("WScript.Shell")
            load_apmx(shell, input.resolve(), timeout=2.5)

        logger.info("Starting spider...")
        controller = SpiderController(
            include_params=parameters,
            include_stack=call_stack,
            output=handler,
        )
        controller.run()
        logger.info("Spider completed successfully.")
    except Exception as e:
        logger.exception(f"Spider failed: {e}")
    finally:
        if proc and proc.poll() is None:
            close_monitor(proc)
            logger.info("Closed API Monitor.")
