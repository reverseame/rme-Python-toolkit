from ioc_extractor.engine.selector import resolve_selector
from ioc_extractor.rules.registry import get_operator


def evaluate_conditions(entry, where):
    if not where:
        return True
    if isinstance(where, dict):
        if "and" in where:
            return all(evaluate_conditions(entry, cond) for cond in where["and"])
        if "or" in where:
            return any(evaluate_conditions(entry, cond) for cond in where["or"])
        if "not" in where:
            return not evaluate_conditions(entry, where["not"])
        if len(where) == 1:
            op, args = next(iter(where.items()))
            op_func = get_operator(op)
            if op_func is None:
                raise ValueError(f"Unknown operator: '{op}'")
            field_path, expected = args
            value = resolve_selector(entry, field_path)
            return op_func(value, expected)
    raise TypeError(f"Invalid condition structure: {where}")
