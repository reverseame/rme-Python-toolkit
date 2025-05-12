import re
from typing import Any

from ioc_extractor.utils.logger import get_logger

logger = get_logger(__name__)

def resolve_selector(entry: dict[str, Any], selector: str) -> Any:
    """
    Navigate nested dictionaries/lists using dot notation (e.g., "foo.bar").
    """
    parts = selector.split(".")
    value: Any = entry
    try:
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and item.get("name") == part:
                        return item.get("post_value") or item.get("pre_value")
                return None
            else:
                return None
            if value is None:
                return None
        return value
    except Exception as e:
        logger.warning(f"Failed to resolve selector '{selector}' in entry: {e}", exc_info=True)
        return None


def apply_modifiers(value: str, modifiers: list[str]) -> str:
    """
    Apply a sequence of transformations to a string value.
    """
    original_value = value
    try:
        for mod in modifiers:
            if mod == "lower":
                value = value.lower()
            elif mod == "upper":
                value = value.upper()
            elif mod == "strip":
                value = value.strip()
            elif mod == "strip_quotes":
                value = re.sub(r"[\"']", "", value).strip()
            elif mod.startswith("regex:"):
                pattern = mod.split("regex:", 1)[1].strip("\"'")
                match = re.search(pattern, value)
                value = match.group(1) if match else value
            else:
                logger.warning(f"Unknown modifier: {mod}")
        logger.debug(f"Applied modifiers {modifiers} to '{original_value}' → '{value}'")
        return value
    except Exception as e:
        logger.error(f"Error applying modifiers {modifiers} to value '{original_value}': {e}", exc_info=True)
        return original_value
