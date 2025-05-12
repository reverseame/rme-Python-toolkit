from typing import Any, Union

from ioc_extractor.rules.registry import _operator_registry
from ioc_extractor.utils.helpers import apply_modifiers, resolve_selector


def evaluate_conditions(value: Any, where: dict[str, Any]) -> bool:
    """
    Recursively evaluate the 'where' clause against the given value.
    Supports empty conditions (always true), logical operators (and/or/not),
    and a default implicit AND for multiple operators at the same level.
    """
    # If there are no conditions, default to True
    if not where:
        return True

    # Logical combinators
    if "and" in where:
        return all(evaluate_conditions(value, cond) for cond in where["and"])
    if "or" in where:
        return any(evaluate_conditions(value, cond) for cond in where["or"])
    if "not" in where:
        return not evaluate_conditions(value, where["not"])

    # Implicit AND for multiple operators at the same level
    results = []
    for op, operand in where.items():
        if op not in _operator_registry:
            raise ValueError(f"Unsupported operator: {op}")
        results.append(_operator_registry[op](value, operand))
    return all(results)


def process_select(
    entry: dict[str, Any], select: list[dict[str, Any]]
) -> dict[str, Any]:
    selected: dict[str, Any] = {}
    for sel in select:
        field = sel["field"]
        alias = sel.get("alias", field)
        transforms = sel.get("transform", [])
        val = resolve_selector(entry, field)
        if isinstance(val, str) and transforms:
            val = apply_modifiers(val, transforms)
        selected[alias] = val

    return {
        "id": entry.get("id", "?"),
        "api": entry.get("api", "?"),
        "fields": selected,
    }


def execute_rule(
    entry: dict[str, Any], rule: dict[str, Any]
) -> Union[dict[str, Any], None]:
    """
    Apply a single rule to an entry.
    Returns the selected result dict if the rule matches, or None otherwise.
    """
    scope = rule.get("from")
    value = resolve_selector(entry, scope)
    if value is None:
        return None
    if not evaluate_conditions(value, rule.get("where", {})):
        return None
    return process_select(entry, rule.get("select", []))
