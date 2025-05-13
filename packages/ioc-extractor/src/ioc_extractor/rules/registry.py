from ioc_extractor.utils.logger import get_logger

logger = get_logger(__name__)

_transform_registry: dict[str, callable] = {}
_operator_registry: dict[str, callable] = {}

def register_transform(name: str):
    def decorator(fn):
        _transform_registry[name] = fn
        return fn
    return decorator

def get_transform(name: str):
    return _transform_registry.get(name)

def register_operator(name: str):
    def decorator(fn):
        _operator_registry[name] = fn
        return fn
    return decorator

def get_operator(name: str):
    return _operator_registry.get(name)

# ---------------------------------------------------------------------
# Auto-load of operators module:
# Ensure that all @register_operator decorators in operators.py
# are executed when this registry is imported.
# ---------------------------------------------------------------------
try:
    from ioc_extractor.rules.operators import *  # noqa: F403
    logger.info("Operators module loaded successfully.")
except ImportError as e:
    logger.warning(f"Operators module could not be loaded: {e}")

try:
    from ioc_extractor.rules.modifiers import *  # noqa: F403
    logger.info("Modifiers module loaded successfully.")
except ImportError as e:
    logger.warning(f"Modifiers module could not be loaded: {e}")
