"""
This module defines and applies value transformation modifiers used in rule definitions.

Modifiers are configured under `transform:` blocks inside YAML rules, and apply transformations to individual fields.

Each modifier can be specified in two formats:

1. Positional form (as a list):

    transform:
    - split: [" ", -1, 1]          # split on space, take index -1, with maxsplit 1
    - regex_sub: ["[\"|']", ""]    # remove quotes

2. Named argument form (as a dictionary):

    transform:
    - split:
        delimiter: " "
        index: -1
        maxsplit: 1
    - regex_sub:
        pattern: "[\"|']"
        repl: ""

Each modifier must be registered with `@register_transform("name")` and must accept a value followed by either *args or **kwargs.
If a modifier is unknown or invalid, it will be skipped with a warning.

Modifiers are evaluated in order.
"""

import logging
import re
import urllib.parse
from typing import Any

from ioc_extractor.rules.registry import get_transform, register_transform

logger = logging.getLogger(__name__)

def to_str(val: Any) -> str:
    if isinstance(val, list):
        return str(val[0]) if val else ""
    return str(val)

def apply_modifiers(value: Any, modifiers: list[Any]) -> str:
    original_value = value
    try:
        for mod in modifiers:
            if isinstance(mod, str):
                name, args, kwargs = mod, [], {}
            elif isinstance(mod, dict) and len(mod) == 1:
                name, param = next(iter(mod.items()))
                if isinstance(param, dict):
                    args, kwargs = [], param
                elif isinstance(param, list):
                    args, kwargs = param, {}
                else:
                    args, kwargs = [param], {}
            else:
                raise TypeError(f"Unsupported modifier format: {mod}")

            fn = get_transform(name)
            if not fn:
                logger.warning(f"Unknown transform: {name}")
                continue

            value = fn(value, *args, **kwargs)

        logger.debug(f"Applied modifiers {modifiers} to '{original_value}' → '{value}'")
        return value
    except Exception as e:
        logger.error(f"Error applying modifiers {modifiers} to value '{original_value}': {e}", exc_info=True)
        return original_value


@register_transform("lower")
def transform_lower(val: Any) -> str:
    return to_str(val).lower()

@register_transform("upper")
def transform_upper(val: Any) -> str:
    return to_str(val).upper()

@register_transform("strip")
def transform_strip(val: Any) -> str:
    return to_str(val).strip()

@register_transform("url_decode")
def transform_url_decode(val: Any) -> str:
    return urllib.parse.unquote(to_str(val))

@register_transform("replace")
def transform_replace(val: Any, pattern: str, repl: str = "") -> str:
    return re.sub(pattern, repl, to_str(val))

@register_transform("regex_extract")
def transform_regex_extract(val: Any, pattern: str, group: int = 1) -> str:
    match = re.search(pattern, to_str(val))
    if match:
        try:
            return match.group(group)
        except IndexError:
            return ""
    return ""

@register_transform("regex_sub")
def transform_regex_sub(val: Any, pattern: str, repl: str = "") -> str:
    return re.sub(pattern, repl, to_str(val))

@register_transform("split")
def transform_split(val: Any, delimiter: str = ",", idx: int = 0, maxsplit: int = -1) -> str:
    parts = to_str(val).split(delimiter, maxsplit)
    return parts[idx].strip()


@register_transform("slice")
def transform_slice(val: Any, start: int = 0, end: int = None, step: int = None) -> str:
    return to_str(val)[start:end:step]
