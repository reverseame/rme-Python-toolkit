import jmespath
from ioc_extractor.rules.registry import get_transform
from ioc_extractor.utils.logger import get_logger

logger = get_logger(__name__)

def resolve_selector(entry: dict, selector: str):
    try:
        return jmespath.search(selector, entry)
    except Exception as e:
        raise RuntimeError(f"JMESPath error in selector '{selector}': {e}")

def apply_modifiers(value: str, modifiers: list[str]) -> str:
    original_value = value
    try:
        for mod in modifiers:
            name, *args = _parse_modifier(mod)
            transform_fn = get_transform(name)
            if not transform_fn:
                logger.warning(f"Unknown transform: {mod}")
                continue
            value = transform_fn(value, *args)
        logger.debug(f"Applied modifiers {modifiers} to '{original_value}' → '{value}'")
        return value
    except Exception as e:
        logger.error(f"Error applying modifiers {modifiers} to value '{original_value}': {e}", exc_info=True)
        return original_value

def _parse_modifier(mod: str | dict) -> tuple[str, list[str]]:
    if isinstance(mod, str):
        if ":" not in mod:
            return mod, []
        name, arg_str = mod.split(":", 1)
        if name == "regex":
            return name, [arg_str.strip()]
        return name, [a.strip() for a in arg_str.split(",")]

    elif isinstance(mod, dict):
        if len(mod) != 1:
            raise ValueError(f"Invalid modifier dict: {mod}")
        name, param = next(iter(mod.items()))
        if isinstance(param, dict):
            return name, [str(param.get("start")), str(param.get("end"))]
        elif isinstance(param, list):
            return name, [str(p) for p in param]
        else:
            return name, [str(param)]

    else:
        raise ValueError(f"Modifier must be str or dict, got {type(mod)}")
