"""
This module implements value transformation logic used in rule definitions.

Transformations (modifiers) are configured under the `transform:` block in YAML rules,
and apply to individual selected fields after extraction. They allow normalization,
cleanup, or parsing of raw field values before being output.

Modifiers are evaluated in the order they are defined and support two formats:

1. Positional (list) syntax:
   transform:
     - lower
     - split: [" ", -1]
     - regex_sub: ["[\"']", ""]  # Remove quotes

2. Named (dict) syntax:
   transform:
     - split:
         delimiter: " "
         index: -1
     - regex_sub:
         pattern: "[\"']"
         repl: ""

Internally, each modifier must be registered using `@register_transform("name")`
and must accept a value followed by *args or **kwargs depending on the input format.

If a modifier is unknown or malformed, it is skipped with a warning.
"""

import logging
import re
import urllib.parse
from typing import Any

from ioc_extractor.rules.registry import get_transform, register_transform

logger = logging.getLogger(__name__)

def to_str(val: Any) -> str:
    """
    Converts any value (or first item of a list) to string for uniform modifier application.
    """
    if isinstance(val, list):
        return str(val[0]) if val else ""
    return str(val)

def apply_modifiers(value: Any, modifiers: list[Any]) -> str:
    """
    Applies a sequence of string transformations to a selected field.
    Supports inline and named-argument modifier syntax from YAML.
    """
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
