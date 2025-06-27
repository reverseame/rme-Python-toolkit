"""
This module defines logical operators used in rule condition evaluation.

Each operator implements a comparison or pattern-matching logic, and is
registered using @register_operator("name"). Operators are invoked dynamically
during rule evaluation via the `where:` clause in YAML rule files.

Example rule snippets:
  - eq: ["status", "success"]
  - gt: ["size", 4096]
  - regex: ["api", "(?i)^Reg(Open|Create)Key(Ex)?$"]
  - in: ["module", ["ntdll.dll", "kernel32.dll"]]
  - range: ["duration", [0.1, 0.5]]

Supported operators include:

▶ Basic comparisons:
  - eq, gt, gte, lt, lte, range

▶ String & pattern matching:
  - contains, not_contains, startswith, endswith, regex

▶ Set & existence checks:
  - in, not_in, exists, not_exists

▶ List-wide logic:
  - match_all (all elements in list match allowed values)
  - match_any (at least one element matches)

Numeric coercion is automatic and includes support for hexadecimal strings
(e.g., "0x20"). Operators return boolean values and fail gracefully on invalid types.
"""

import re
from typing import Any, Union

from ioc_extractor.rules.registry import register_operator


def parse_numeric(val: Any) -> float | None:
    """
    Parses string or numeric input into a float if possible.
    Supports hex strings like '0x10' for numerical comparisons.
    """
    try:
        if isinstance(val, str) and val.lower().startswith("0x"):
            return float(int(val, 16))
        return float(val)
    except (ValueError, TypeError):
        return None


# ──────────────────────────────
# Basic Comparison Operators
# ──────────────────────────────


@register_operator("eq")
def op_eq(value: Any, operand: Any) -> bool:
    v = parse_numeric(value)
    o = parse_numeric(operand)
    if v is not None and o is not None:
        return v == o
    return value == operand


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


# ──────────────────────────────
# String & Pattern Operators
# ──────────────────────────────


@register_operator("contains")
def op_contains(value: str, operand: str) -> bool:
    return operand in value


@register_operator("not_contains")
def op_not_contains(value: str, operand: str) -> bool:
    return operand not in value


@register_operator("startswith")
def op_startswith(value: str, operand: str) -> bool:
    return value.startswith(operand)


@register_operator("endswith")
def op_endswith(value: str, operand: str) -> bool:
    return value.endswith(operand)


@register_operator("regex")
def op_regex(value: str, pattern: Union[str, re.Pattern]) -> bool:
    if isinstance(pattern, re.Pattern):
        return bool(pattern.search(value))
    return bool(re.search(pattern, value))


# ──────────────────────────────
# Set & Existence Operators
# ──────────────────────────────


@register_operator("in")
def op_in(value: Any, operand: list[Any]) -> bool:
    return value in operand


@register_operator("not_in")
def op_not_in(value: Any, operand: list[Any]) -> bool:
    return value not in operand


@register_operator("exists")
def op_exists(value: Any) -> bool:
    return value is not None and value != ""


@register_operator("not_exists")
def op_not_exists(value: Any) -> bool:
    return value is None or value == ""


# ──────────────────────────────
# List Matching Operators
# ──────────────────────────────


@register_operator("match_all")
def op_match_all(value: Any, allowed: list[Any]) -> bool:
    return isinstance(value, list) and all(item in allowed for item in value)


@register_operator("match_any")
def op_match_any(value: Any, allowed: list[Any]) -> bool:
    return isinstance(value, list) and any(item in allowed for item in value)


# ──────────────────────────────
# Range Operator
# ──────────────────────────────


@register_operator("range")
def op_range(value: Any, bounds: list[Any]) -> bool:
    if not isinstance(bounds, list) or len(bounds) != 2:
        return False
    v = parse_numeric(value)
    low, high = map(parse_numeric, bounds)
    return v is not None and low is not None and high is not None and low <= v <= high
