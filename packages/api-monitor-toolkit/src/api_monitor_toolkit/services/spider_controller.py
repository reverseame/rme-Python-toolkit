import re
import time
from rich.progress import Progress, BarColumn, TimeElapsedColumn, TimeRemainingColumn, MofNCompleteColumn
import sys
from pathlib import Path
from typing import Any, Callable, Optional

import commctrl as cc
import win32con as wc
import win32gui
from api_monitor_toolkit.core.discovery import (
    find_control,
    find_controls,
    find_main_window,
)
from api_monitor_toolkit.core.exceptions import ChildControlsNotFound
from api_monitor_toolkit.core.remote import RemoteListView, RemoteTreeView
from api_monitor_toolkit.output.handler import OutputHandler
from api_monitor_toolkit.utils.mappings import (
    CALLSTACK_MAPPING,
    PARAMS_MAPPING,
    SUMMARY_MAPPING,
)
from api_monitor_toolkit.utils.value_transformer import ValueTransformer
from common.logger import get_logger

logger = get_logger(__name__)


class SpiderController:
    def __init__(
        self, include_params: bool, include_stack: bool, output: OutputHandler
    ):
        self.include_params = include_params
        self.include_stack = include_stack
        self.output = output
        self.transformer = ValueTransformer()

    def run(self):
        self.output.start()
        try:
            main_hwnd = find_main_window(lambda t: "API Monitor v2" in t)
            tree_hwnd = find_control(
                main_hwnd, lambda h: win32gui.GetClassName(h) == "SysTreeView32"
            )
            with RemoteTreeView(tree_hwnd) as tree:
                for label, node in tree.walk_roots():
                    logger.info(f"Processing node: {label}")
                    metadata = self._extract_metadata(label)
                    if not metadata:
                        continue
                    self._select_node(tree_hwnd, node)
                    self._process_summary(main_hwnd, metadata)
        finally:
            self.output.finish()

    def _extract_metadata(self, label: str) -> Optional[dict]:
        match = re.match(r"(.+?)\s+-\s+PID:\s+(\d+)", label)
        if not match:
            logger.warning(f"Invalid node label format: {label}")
            return None
        path, pid = match.groups()
        return {"path": path, "filename": Path(path).name, "pid": int(pid)}

    def _select_node(self, tree_hwnd: int, node_hwnd: int):
        win32gui.SendMessage(tree_hwnd, cc.TVM_SELECTITEM, cc.TVGN_CARET, node_hwnd)
        win32gui.PostMessage(tree_hwnd, wc.WM_KEYDOWN, wc.VK_RETURN, 0)
        time.sleep(0.1)

    def _process_summary(self, main_hwnd: int, metadata: dict):
        try:
            panel = find_controls(
                main_hwnd, lambda h: "Summary" in win32gui.GetWindowText(h)
            )[0]
            header = find_control(
                panel, lambda h: win32gui.GetClassName(h) == "SysHeader32"
            )
            listview = find_control(
                panel, lambda h: win32gui.GetClassName(h) == "SysListView32"
            )
        except (ChildControlsNotFound, IndexError):
            logger.warning(f"Summary panel not found for PID={metadata['pid']}")
            return

        if not self._wait_for_list_data(listview):
            logger.warning(
                f"No summary entries loaded for {metadata['filename']} (PID={metadata['pid']})"
            )
            return

        with RemoteListView(header, listview) as view:
            headers = view.get_columns()
            indices, names = view._select_columns(headers, None)
            total = win32gui.SendMessage(listview, cc.LVM_GETITEMCOUNT, 0, 0)
            logger.info(f"{total} entries found for {metadata['filename']}")

            with Progress(
                "[progress.description]{task.description}",
                BarColumn(),
                MofNCompleteColumn(),
                TimeElapsedColumn(),
                TimeRemainingColumn(),
                transient=False,
            ) as progress:
                task = progress.add_task("Progress", total=total)
                for i in range(total):
                    row = view._read_row(i, len(headers))
                    entry = {
                        (
                            mapped := SUMMARY_MAPPING.get(names[j], names[j])
                        ): self.transformer.transform(mapped, row[col])
                        for j, col in enumerate(indices)
                    }

                    view.select(i)
                    if self.include_params:
                        entry["parameters"] = self._get_mapped_panel_data(
                            main_hwnd,
                            "Parameters",
                            PARAMS_MAPPING,
                            skip_penultimate_empty=True,
                        )
                    if self.include_stack:
                        entry["call_stack"] = self._get_mapped_panel_data(
                            main_hwnd, "Call Stack", CALLSTACK_MAPPING
                        )

                    entry["metadata"] = metadata
                    self.output.write(entry)
                    progress.update(task, advance=1)

    def _wait_for_list_data(
        self, listview_hwnd: int, retries: int = 5, delay: float = 0.2
    ) -> bool:
        for _ in range(retries):
            total = win32gui.SendMessage(listview_hwnd, cc.LVM_GETITEMCOUNT, 0, 0)
            if total > 0:
                return True
            time.sleep(delay)
        return False

    def _get_mapped_panel_data(
        self,
        main_hwnd: int,
        panel_title: str,
        mapping: dict[str, str],
        skip_penultimate_empty: bool = False,
    ) -> list[dict[str, Any]]:
        try:
            window = find_controls(
                main_hwnd, lambda h: panel_title in win32gui.GetWindowText(h)
            )[0]
            header = find_control(
                window, lambda h: win32gui.GetClassName(h) == "SysHeader32"
            )
            listview = find_control(
                window, lambda h: win32gui.GetClassName(h) == "SysListView32"
            )

            with RemoteListView(header, listview) as view:
                data = view.as_json()
                mapped = []

                for i, row in enumerate(data):
                    if skip_penultimate_empty and i == len(data) - 2:
                        if not any(cell.strip() for cell in row.values()):
                            continue
                    mapped.append(
                        {
                            (
                                mapped_key := mapping.get(k, k)
                            ): self.transformer.transform(mapped_key, v)
                            for k, v in row.items()
                        }
                    )

                return mapped
        except Exception as e:
            logger.warning(f"Failed to extract '{panel_title}' data: {e}")
            return []
