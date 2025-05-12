from shutil import get_terminal_size
from typing import Any

from ioc_extractor.utils.logger import console
from rich.console import Console
from rich.style import Style
from rich.text import Text

# Configurable constants
DEFAULT_TERMINAL_WIDTH = 100
DEFAULT_TERMINAL_HEIGHT = 20
FIELD_NAME_WIDTH = 24
INDENTATION = "    "
HEADER_COLOR = "white"
HIGHLIGHT_COLOR = "bold red"
FILENAME_COLOR = "bold green"
FIELD_NAME_STYLE = Style(color="cyan")
SEPARATOR_STYLE = "white"
FIELD_VALUE_STYLE = Style(dim=True)


def print_match(
    match_type: str,
    match_id: str,
    api: str,
    source_file: str,
    selected_fields: dict[str, Any],
) -> None:
    api_short = api.split("(")[0].strip()

    # Get terminal width
    term_width = get_terminal_size(
        (DEFAULT_TERMINAL_WIDTH, DEFAULT_TERMINAL_HEIGHT)
    ).columns

    # Build header line
    header = Text()
    header.append("[+] IOC: ", style=HEADER_COLOR)
    header.append(match_type, style=HIGHLIGHT_COLOR)
    header.append(" | ID: ", style=HEADER_COLOR)
    header.append(str(match_id), style=HIGHLIGHT_COLOR)
    header.append(" | API: ", style=HEADER_COLOR)
    header.append(api_short, style=HIGHLIGHT_COLOR)

    # Align file name to the right
    plain_header = header.plain
    total_padding = (
        term_width - len(plain_header) - len(source_file) - 2
    )  # 2 for brackets
    if total_padding > 0:
        header.append(" " * total_padding)
    header.append(f"[{source_file}]", style=FILENAME_COLOR)

    console.print(header)

    if not selected_fields:
        return

    for key in sorted(selected_fields):
        key_text = f"{key:<{FIELD_NAME_WIDTH}}"
        value_text = str(selected_fields[key])
        line = Text(INDENTATION)
        line.append(key_text, style=FIELD_NAME_STYLE)
        line.append(": ", style=SEPARATOR_STYLE)
        line.append(value_text, style=FIELD_VALUE_STYLE)
        console.print(line)
