import re
import time
from pathlib import Path
from typing import Annotated, Optional

import commctrl as cc
import typer
import win32con as wc
import win32gui
from api_monitor_toolkit.core.discovery import (
    find_child_windows,
    find_control,
    find_main_window,
)
from api_monitor_toolkit.core.exceptions import (
    ChildControlsNotFound,
    MainWindowNotFound,
)
from api_monitor_toolkit.core.remote import RemoteListView, RemoteTreeView
from api_monitor_toolkit.utils.callbacks import verbose_callback
from api_monitor_toolkit.utils.helpers import ValueTransformer, get_mapped_data
from api_monitor_toolkit.utils.mappings import (
    CALLSTACK_MAPPING,
    PARAMS_MAPPING,
    SUMMARY_MAPPING,
)
from api_monitor_toolkit.utils.output import choose_output_handler
from common.logger import get_logger

logger = get_logger(__name__)
app = typer.Typer()


def extract_metadata(tree_node_text: str) -> dict:
    """
    Extracts path, filename and PID from the root TreeView node text.
    """
    match = re.match(r"(.+?)\s+-\s+PID:\s+(\d+)\s+-\s+\(.+?\)", tree_node_text)
    if not match:
        logger.warning(
            f"Failed to parse metadata from tree node text: {tree_node_text}"
        )
        return {}

    full_path, pid = match.groups()
    return {"path": full_path, "filename": Path(full_path).name, "pid": int(pid)}


def process_summary_for_node(
    main_window: int,
    transformer: ValueTransformer,
    include_params: bool,
    include_stack: bool,
) -> list[dict]:
    """
    Locates and processes summary entries for the currently selected TreeView node.
    """
    try:
        summary_window = find_child_windows(
            main_window, lambda hwnd: "Summary" in win32gui.GetWindowText(hwnd)
        )[0]
        header_summary = find_control(
            summary_window, lambda hwnd: win32gui.GetClassName(hwnd) == "SysHeader32"
        )
        list_summary = find_control(
            summary_window, lambda hwnd: win32gui.GetClassName(hwnd) == "SysListView32"
        )
    except (ChildControlsNotFound, IndexError):
        logger.warning("No summary controls found for current node.")
        return []

    results = []

    with RemoteListView(header_summary, list_summary) as summary_view:
        summary_rows = summary_view.as_json()

        for idx, row in enumerate(summary_rows):
            entry = {
                (mapped := SUMMARY_MAPPING.get(k, k)): transformer.transform(mapped, v)
                for k, v in row.items()
            }

            if include_params or include_stack:
                summary_view.select(idx)

            if include_params:
                entry["parameters"] = get_mapped_data(
                    main_window,
                    "Parameters",
                    PARAMS_MAPPING,
                    transformer,
                    skip_penultimate_empty=True,
                )

            if include_stack:
                entry["call_stack"] = get_mapped_data(
                    main_window, "Call Stack", CALLSTACK_MAPPING, transformer
                )

            results.append(entry)

    return results


@app.command()
def spider(
    parameters: Annotated[
        Optional[bool],
        typer.Option("-p", "--parameters", help="Include Parameters section"),
    ] = False,
    call_stack: Annotated[
        Optional[bool],
        typer.Option("-c", "--call-stack", help="Include Call Stack section"),
    ] = False,
    output: Annotated[
        Optional[str],
        typer.Option(
            "-o", "--output", help="Output destination: file path or HTTP URL"
        ),
    ] = None,
    verbosity: Annotated[
        int,
        typer.Option(
            "-v",
            "--verbose",
            count=True,
            callback=verbose_callback,
            help="Increase output verbosity (use multiple times)",
        ),
    ] = 0,
) -> None:
    try:
        transformer = ValueTransformer()
        output_handler = choose_output_handler(output)
        output_handler.start()

        main_window = find_main_window(lambda title: "API Monitor v2" in title)
        treeview_hwnd = find_control(
            main_window, lambda hwnd: win32gui.GetClassName(hwnd) == "SysTreeView32"
        )

        with RemoteTreeView(treeview_hwnd) as tree:
            for node_text, node_handle in tree.walk_roots():
                logger.info(f"Processing tree node: {node_text}")
                metadata = extract_metadata(node_text)

                # Select the node in the TreeView UI
                win32gui.SendMessage(
                    treeview_hwnd, cc.TVM_SELECTITEM, cc.TVGN_CARET, node_handle
                )
                win32gui.PostMessage(treeview_hwnd, wc.WM_KEYDOWN, wc.VK_RETURN, 0)
                time.sleep(0.1)  # Give UI time to update

                # Process summary rows for this node
                entries = process_summary_for_node(
                    main_window, transformer, parameters, call_stack
                )

                for entry in entries:
                    entry["metadata"] = metadata
                    output_handler.write(entry)

        output_handler.finish()

    except MainWindowNotFound:
        logger.error(
            "Failed to locate the main application window. Is API Monitor running?"
        )
    except ChildControlsNotFound:
        logger.warning("No TreeView control found in the target window.")
