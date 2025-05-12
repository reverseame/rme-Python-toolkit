import re
from typing import Any


def resolve_selector(entry: dict[str, Any], selector: str) -> Any:
    parts = selector.split(".")
    value: Any = entry
    for part in parts:
        if isinstance(value, dict):
            value = value.get(part)
        elif isinstance(value, list):
            for item in value:
                if item.get("name") == part:
                    return item.get("post_value") or item.get("pre_value")
            return None
        else:
            return None
        if value is None:
            return None
    return value


def apply_modifiers(value: str, modifiers: list[str]) -> str:
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
    return value
