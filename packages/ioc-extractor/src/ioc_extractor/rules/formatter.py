from typing import Any

from ioc_extractor.utils.logger import get_logger

logger = get_logger(__name__)

FIELD_NAME_WIDTH = 24
INDENTATION = "    "

def print_match(
    match_type: str,
    match_id: str,
    api: str,
    source_file: str,
    selected_fields: dict[str, Any],
) -> None:
    """
    Print match information in a single logger.info() call with rich markup styling.
    Safe for multiprocessing.
    """
    try:
        api_short = api.split("(")[0].strip()

        # Header line
        lines = [
            f"IOC [bold cyan]{match_type}[/bold cyan] "
            f"ID [bold cyan]{str(match_id)}[/bold cyan] "
            f"API [bold cyan]{api_short}[/bold cyan] "
            f"[bold green][{source_file}][/bold green]"
        ]

        # Field lines
        for key in sorted(selected_fields):
            key_text = f"[magenta]{key:<{FIELD_NAME_WIDTH}}[/magenta]"
            value_text = f"[dim]{selected_fields[key]}[/dim]"
            lines.append(f"{INDENTATION}{key_text}: {value_text}")

        logger.info("\n".join(lines))
        logger.debug(f"Printed match info: type={match_type}, id={match_id}, file={source_file}")

    except Exception as e:
        logger.error(f"Failed to print match (type={match_type}, id={match_id}): {e}", exc_info=True)
