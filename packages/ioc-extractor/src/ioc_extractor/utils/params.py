from typing import Any


def normalize_parameters(entry: dict[str, Any]) -> dict[str, Any]:
    params = entry.get("parameters")
    if isinstance(params, list):
        param_dict = {}
        for p in params:
            name = p.get("name")
            value = p.get("post_value") or p.get("pre_value")
            if name:
                param_dict[name] = value
        entry["parameters"] = param_dict
    return entry
