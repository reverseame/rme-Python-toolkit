from typing import Any

from common.logger import get_logger

logger = get_logger(__name__)

FIELD_NAME_WIDTH = 18
INDENTATION = "    "


def normalize_to_list(val):
    if val is None:
        return []
    return val if isinstance(val, list) else [val]


def build_rule_name(meta: dict, variant: str | None) -> str:
    rule_base = meta.get("name", "unnamed")
    if not variant or variant == rule_base:
        return rule_base
    return f"{rule_base}::{variant}"


def print_match(
    match_type: str,
    api: str,
    source_file: str,
    selected_fields: dict[str, Any],
) -> None:
    """
    Print match information including selected fields and source file.
    Format: MATCH rule::variant → API (source_file)
            key1        : value1
            key2        : value2
    """
    try:
        lines = [
            f"[bold green]MATCH[/bold green] [bold white]{match_type}[/bold white] → [cyan]{api}[/cyan] [dim]({source_file})[/dim]"
        ]
        if selected_fields:
            for key in sorted(selected_fields):
                label = f"{key:<{FIELD_NAME_WIDTH}}"
                value = selected_fields[key]
                lines.append(
                    f"{INDENTATION}[magenta]{label}[/magenta]: [dim]{value}[/dim]"
                )

        logger.info("\n".join(lines))
    except Exception as e:
        logger.error(f"Failed to print match (type={match_type}): {e}", exc_info=True)
