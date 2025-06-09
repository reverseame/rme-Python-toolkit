import re
import time
from pathlib import Path
from typing import Optional, Callable, Annotated

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
from common.callbacks import verbose_callback
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


def extract_metadata(node_text: str) -> Optional[dict]:
    """
    Extract the executable path and PID from a tree node label.
    Return metadata dict or None if parsing fails.
    """
    match = re.match(r"(.+?)\s+-\s+PID:\s+(\d+)", node_text)
    if not match:
        logger.warning(f"Skipping node with invalid metadata: {node_text}")
        return None
    executable, pid = match.groups()
    return {"path": executable, "filename": Path(executable).name, "pid": int(pid)}


def process_summary(
    main_hwnd: int,
    transformer: ValueTransformer,
    include_params: bool,
    include_stack: bool,
    metadata: dict,
    write: Callable[[dict], None],
) -> None:
    """
    Stream summary entries for the selected node and write each entry.
    """
    try:
        summary_hwnd = find_child_windows(
            main_hwnd, lambda h: "Summary" in win32gui.GetWindowText(h)
        )[0]
        header_hwnd = find_control(
            summary_hwnd, lambda h: win32gui.GetClassName(h) == "SysHeader32"
        )
        list_hwnd = find_control(
            summary_hwnd, lambda h: win32gui.GetClassName(h) == "SysListView32"
        )
    except (ChildControlsNotFound, IndexError):
        logger.warning(f"Summary panel not found for PID={metadata['pid']}")
        return

    # Wait briefly for the list view to populate
    for attempt in range(5):
        total = win32gui.SendMessage(list_hwnd, cc.LVM_GETITEMCOUNT, 0, 0)
        if total > 0:
            break
        time.sleep(0.2)
    else:
        logger.warning(f"No summary entries loaded for PID={metadata['pid']}")
        return

    with RemoteListView(header_hwnd, list_hwnd) as view:
        headers = view.get_columns()
        indices, names = view._select_columns(headers, None)
        logger.info(f"Found {total} summary entries for {metadata['filename']} (PID={metadata['pid']})")

        for idx in range(total):
            row = view._read_row(idx, len(headers))
            entry = {names[j]: transformer.transform(names[j], row[col])
                     for j, col in enumerate(indices)}
            if include_params:
                view.select(idx)
                entry["parameters"] = get_mapped_data(
                    main_hwnd, "Parameters", PARAMS_MAPPING,
                    transformer, skip_penultimate_empty=True
                )
            if include_stack:
                view.select(idx)
                entry["call_stack"] = get_mapped_data(
                    main_hwnd, "Call Stack", CALLSTACK_MAPPING, transformer
                )
            entry["metadata"] = metadata
            write(entry)


@app.command()
def spider(
    parameters: Annotated[Optional[bool], typer.Option("-p", "--parameters")]=False,
    call_stack: Annotated[Optional[bool], typer.Option("-c", "--call-stack")]=False,
    output: Annotated[Optional[str], typer.Option("-o", "--output")]=None,
    verbosity: Annotated[int, typer.Option("-v", count=True, callback=verbose_callback)]=0,
) -> None:
    logger.info("Starting API Monitor spider")
    handler = None
    try:
        transformer = ValueTransformer()
        handler = choose_output_handler(output)
        # define write callback that flushes immediately if possible
        def write_and_flush(entry: dict):
            handler.write(entry)
            try:
                handler.file.flush()
            except Exception:
                pass
        write_callback = write_and_flush

        logger.info(f"Output handler: {handler.__class__.__name__}")
        handler.start()

        main_hwnd = find_main_window(lambda t: "API Monitor v2" in t)
        tree_hwnd = find_control(
            main_hwnd, lambda h: win32gui.GetClassName(h) == "SysTreeView32"
        )

        with RemoteTreeView(tree_hwnd) as tree:
            for node_text, node_hwnd in tree.walk_roots():
                logger.info(f"Processing node: {node_text}")
                metadata = extract_metadata(node_text)
                if not metadata:
                    continue

                # select node and trigger summary load
                win32gui.SendMessage(
                    tree_hwnd, cc.TVM_SELECTITEM, cc.TVGN_CARET, node_hwnd
                )
                win32gui.PostMessage(tree_hwnd, wc.WM_KEYDOWN, wc.VK_RETURN, 0)
                time.sleep(0.1)

                process_summary(
                    main_hwnd,
                    transformer,
                    parameters,
                    call_stack,
                    metadata,
                    write_callback,
                )

        logger.info("Spider completed successfully")
    except MainWindowNotFound:
        logger.error("API Monitor main window not found; ensure it's running")
    except Exception as exc:
        logger.exception(f"Spider failed: {exc}")
    finally:
        if handler:
            handler.finish()
