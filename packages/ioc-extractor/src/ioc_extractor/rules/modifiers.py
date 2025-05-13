# transforms.py — sistema robusto de transformadores para reglas

import logging
import re
import urllib.parse
from typing import Any

from ioc_extractor.rules.registry import get_transform, register_transform

logger = logging.getLogger(__name__)

def _normalize_value(val: Any) -> str:
    """Convierte listas en strings usando el primer valor, si aplica."""
    if isinstance(val, list):
        val = val[0] if val else ""
    return str(val)

def apply_modifiers(value: Any, modifiers: list[Any]) -> str:
    """Aplica una secuencia de transformaciones al valor dado."""
    original_value = value
    try:
        for mod in modifiers:
            if isinstance(mod, str):
                if ":" in mod:
                    name, arg_str = mod.split(":", 1)
                    args = [arg.strip() for arg in arg_str.split(",")]
                else:
                    name, args = mod, []
            elif isinstance(mod, dict):
                if len(mod) != 1:
                    raise ValueError(f"Invalid modifier dict: {mod}")
                name, params = next(iter(mod.items()))
                if isinstance(params, dict):
                    args = [str(params.get("start")), str(params.get("end"))]
                elif isinstance(params, list):
                    args = [str(p) for p in params]
                else:
                    args = [str(params)]
            else:
                raise TypeError(f"Unsupported modifier type: {type(mod)}")

            transform_fn = get_transform(name)
            if not transform_fn:
                logger.warning(f"Unknown transform: {name}")
                continue
            value = transform_fn(value, *args)

        logger.debug(f"Applied modifiers {modifiers} to '{original_value}' → '{value}'")
        return value
    except Exception as e:
        logger.error(f"Error applying modifiers {modifiers} to value '{original_value}': {e}", exc_info=True)
        return original_value

@register_transform("lower")
def transform_lower(val: Any, *args) -> str:
    return _normalize_value(val).lower()

@register_transform("upper")
def transform_upper(val: Any, *args) -> str:
    return _normalize_value(val).upper()

@register_transform("strip")
def transform_strip(val: Any, *args) -> str:
    return _normalize_value(val).strip()

@register_transform("url_decode")
def transform_url_decode(val: Any, *args) -> str:
    return urllib.parse.unquote(_normalize_value(val))

@register_transform("regex")
def transform_regex(val: Any, pattern: str | list) -> str:
    val = _normalize_value(val)
    if isinstance(pattern, list):
        pattern = pattern[0]  # protección extra
    match = re.search(pattern, val)
    return match.group(1) if match else val

@register_transform("replace")
def transform_replace(val: Any, pattern: str, repl: str) -> str:
    val = _normalize_value(val)
    return re.sub(pattern, repl, val)

@register_transform("split")
def transform_split(val: Any, delimiter: str) -> str:
    val = _normalize_value(val)
    return val.split(delimiter)[0].strip()

@register_transform("substring")
def transform_substring(val: Any, start: str, end: str = None) -> str:
    val = _normalize_value(val)
    s = int(start)
    e = int(end) if end not in (None, "None") else None
    return val[s:e]
