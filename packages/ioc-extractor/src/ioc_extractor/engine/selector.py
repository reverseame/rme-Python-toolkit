import jmespath
from ioc_extractor.rules.modifiers import apply_modifiers
from ioc_extractor.utils.logger import get_logger

logger = get_logger(__name__)


def resolve_selector(entry: dict, selector: str):
    """Evaluates a JMESPath expression on a JSON-like entry."""
    try:
        return jmespath.search(selector, entry)
    except Exception as e:
        logger.warning(f"Failed to resolve selector '{selector}': {e}")
        return None


def process_select(entry: dict, select_list: list[dict]) -> dict:
    """
    Applies 'select' logic from a rule: extracts fields, applies transformations,
    and returns them with aliases for use in rule output.
    """
    fields = {}
    for sel in select_list:
        field = sel["field"]
        alias = sel.get("alias", field)
        transforms = sel.get("transform", [])
        val = resolve_selector(entry, field)

        if isinstance(val, list):
            if len(val) == 1:
                val = val[0]
            elif not val:
                val = None

        if isinstance(val, str) and transforms:
            val = apply_modifiers(val, transforms)
        fields[alias] = val

    return {
        "id": entry.get("id", "?"),
        "api": entry.get("api", "?"),
        "fields": fields,
    }
