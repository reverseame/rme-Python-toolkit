import re
from typing import Any, Union

from ioc_extractor.rules.registry import register_operator


def parse_numeric(val: Any) -> Union[float, None]:
    try:
        if isinstance(val, str) and val.lower().startswith("0x"):
            return float(int(val, 16))
        return float(val)
    except (ValueError, TypeError):
        return None


@register_operator("contains")
def op_contains(value: str, operand: str) -> bool:
    return operand in value


@register_operator("not_contains")
def op_not_contains(value: str, operand: str) -> bool:
    return operand not in value


@register_operator("regex")
def op_regex(value: str, pattern: Union[str, re.Pattern]) -> bool:
    # Accept either a precompiled regex or a string
    if isinstance(pattern, re.Pattern):
        return bool(pattern.search(value))
    return bool(re.search(pattern, value))


@register_operator("eq")
def op_eq(value: Any, operand: Any) -> bool:
    v = parse_numeric(value)
    o = parse_numeric(operand)
    if v is not None and o is not None:
        return v == o
    return value == operand


@register_operator("startswith")
def op_startswith(value: str, operand: str) -> bool:
    return value.startswith(operand)


@register_operator("endswith")
def op_endswith(value: str, operand: str) -> bool:
    return value.endswith(operand)


@register_operator("in")
def op_in(value: Any, operand: list[Any]) -> bool:
    return value in operand


@register_operator("not_in")
def op_not_in(value: Any, operand: list[Any]) -> bool:
    return value not in operand


@register_operator("gt")
def op_gt(value: Any, operand: Any) -> bool:
    v = parse_numeric(value)
    o = parse_numeric(operand)
    return v is not None and o is not None and v > o


@register_operator("gte")
def op_gte(value: Any, operand: Any) -> bool:
    v = parse_numeric(value)
    o = parse_numeric(operand)
    return v is not None and o is not None and v >= o


@register_operator("lt")
def op_lt(value: Any, operand: Any) -> bool:
    v = parse_numeric(value)
    o = parse_numeric(operand)
    return v is not None and o is not None and v < o


@register_operator("lte")
def op_lte(value: Any, operand: Any) -> bool:
    v = parse_numeric(value)
    o = parse_numeric(operand)
    return v is not None and o is not None and v <= o
