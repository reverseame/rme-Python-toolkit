from typing import Any

from ioc_extractor.utils.logger import get_logger

logger = get_logger(__name__)

FIELD_NAME_WIDTH = 18
INDENTATION = "    "

def normalize_to_list(val):
    if val is None:
        return []
    return val if isinstance(val, list) else [val]

def format_result(entry_id, api_full, selected_fields, rule) -> dict:
    api_short = api_full.split("(")[0].strip()
    meta = rule.get("meta", {})
    variant = rule.get("name")

    # Construcción del nombre compuesto de la regla
    if not variant or variant == meta.get("name"):
        rule_name = meta.get("name", variant or "unnamed")
    else:
        rule_name = f"{meta.get('name')}::{variant}"

    def merge(field):
        return sorted(set(normalize_to_list(meta.get(field, [])) + normalize_to_list(rule.get(field, []))))

    metadata = {"rule": rule_name}
    for field in ("mbcs", "att&ck", "tags", "categories"):
        merged = merge(field)
        if merged:
            metadata[field] = merged

    return {
        "id": entry_id,
        "api": api_short,
        "attributes": selected_fields,
        "metadata": metadata
    }

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
