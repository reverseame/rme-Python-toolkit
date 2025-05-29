import typer
import win32gui
from api_monitor_toolkit.utils.output import choose_output_handler
from typing import Annotated, Optional
from api_monitor_toolkit.utils.helpers import ValueTransformer, get_mapped_data
from api_monitor_toolkit.utils.mappings import SUMMARY_MAPPING, PARAMS_MAPPING, CALLSTACK_MAPPING
from api_monitor_toolkit.core.remote import RemoteListView
from api_monitor_toolkit.utils.callbacks import verbose_callback
from api_monitor_toolkit.utils.logger import get_logger
from api_monitor_toolkit.core.discovery import (
    find_main_window,
    find_child_windows,
    find_control
)
from api_monitor_toolkit.core.exceptions import MainWindowNotFound, ChildControlsNotFound

logger = get_logger(__name__)
app = typer.Typer()

@app.command()
def spider(
    parameters: Annotated[
        Optional[bool],
        typer.Option("-p", "--parameters", help="Include Parameters section")
    ] = False,
    call_stack: Annotated[
        Optional[bool],
        typer.Option("-c", "--call-stack", help="Include Call Stack section")
    ] = False,
    output: Annotated[
        Optional[str],
        typer.Option("-o", "--output", help="Output destination: file path or HTTP URL")
    ] = None,
    verbosity: Annotated[
        int,
        typer.Option(
            "-v", "--verbose",
            count=True,
            callback=verbose_callback,
            help="Increase output verbosity (use multiple times)"
        )
    ] = 0,
) -> None:
    try:
        transformer = ValueTransformer()
        output_handler = choose_output_handler(output)

        main_window = find_main_window(lambda title: "API Monitor v2" in title)
        summary_window = find_child_windows(main_window, lambda hwnd: "Summary" in win32gui.GetWindowText(hwnd))[0]

        header_summary = find_control(summary_window, lambda hwnd: win32gui.GetClassName(hwnd) == "SysHeader32")
        list_summary = find_control(summary_window, lambda hwnd: win32gui.GetClassName(hwnd) == "SysListView32")

        with RemoteListView(header_summary, list_summary) as summary_view:
            summary_rows = summary_view.as_json()

            output_handler.start()

            for idx, row in enumerate(summary_rows):
                entry = {
                    (mapped := SUMMARY_MAPPING.get(k, k)): transformer.transform(mapped, v)
                    for k, v in row.items()
                }

                if parameters or call_stack:
                    summary_view.select(idx)

                if parameters:
                    entry["parameters"] = get_mapped_data(
                        main_window, "Parameters", PARAMS_MAPPING, transformer, skip_penultimate_empty=True
                    )

                if call_stack:
                    entry["call_stack"] = get_mapped_data(
                        main_window, "Call Stack", CALLSTACK_MAPPING, transformer
                    )

                output_handler.write(entry)

            output_handler.finish()

    except MainWindowNotFound:
        logger.error("Failed to locate the main application window. Is API Monitor running?")
    except ChildControlsNotFound:
        logger.warning("No ListView controls found in the target window.")