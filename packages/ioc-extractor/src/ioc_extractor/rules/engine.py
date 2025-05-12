from typing import Any, Union

from ioc_extractor.rules.registry import _operator_registry
from ioc_extractor.utils.helpers import apply_modifiers, resolve_selector
from ioc_extractor.utils.logger import get_logger

logger = get_logger(__name__)

def evaluate_conditions(value: Any, where: dict[str, Any]) -> bool:
    """
    Recursively evaluate the 'where' clause against the given value.
    Supports logical operators and implicit AND.
    """
    if not where:
        logger.debug("No conditions specified; defaulting to True")
        return True

    try:
        if "and" in where:
            result = all(evaluate_conditions(value, cond) for cond in where["and"])
            return result
        if "or" in where:
            result = any(evaluate_conditions(value, cond) for cond in where["or"])
            return result
        if "not" in where:
            result = not evaluate_conditions(value, where["not"])
            return result

        results = []
        for op, operand in where.items():
            if op not in _operator_registry:
                logger.error(f"Unsupported operator: '{op}'")
                raise ValueError(f"Unsupported operator: {op}")
            result = _operator_registry[op](value, operand)
            results.append(result)
        final = all(results)
        return final

    except Exception as e:
        logger.error(f"Error evaluating conditions: {e}", exc_info=True)
        raise

def process_select(entry: dict[str, Any], select: list[dict[str, Any]]) -> dict[str, Any]:
    selected: dict[str, Any] = {}
    try:
        for sel in select:
            field = sel["field"]
            alias = sel.get("alias", field)
            transforms = sel.get("transform", [])
            val = resolve_selector(entry, field)
            logger.debug(f"Resolved field '{field}' to value: {val}")

            if isinstance(val, str) and transforms:
                val = apply_modifiers(val, transforms)
                logger.debug(f"Applied transforms on '{field}': {transforms} -> {val}")

            selected[alias] = val

        return {
            "id": entry.get("id", "?"),
            "api": entry.get("api", "?"),
            "fields": selected,
        }
    except Exception as e:
        logger.error(f"Error during field selection and transformation: {e}", exc_info=True)
        raise

def execute_rule(entry: dict[str, Any], rule: dict[str, Any]) -> Union[dict[str, Any], None]:
    """
    Apply a single rule to an entry.
    Returns selected data if the rule matches.
    """
    try:
        scope = rule.get("from")
        value = resolve_selector(entry, scope)
        if value is None:
            logger.debug(f"Scope '{scope}' not found in entry; skipping rule '{rule.get('name')}'")
            return None

        if not evaluate_conditions(value, rule.get("where", {})):
            return None

        result = process_select(entry, rule.get("select", []))
        return result

    except Exception as e:
        logger.warning(f"Failed to execute rule '{rule.get('name')}' on entry: {e}", exc_info=True)
        return None
