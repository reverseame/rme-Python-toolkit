from typing import Any, Callable

from ioc_extractor.utils.logger import get_logger

logger = get_logger(__name__)

# Mapping of operator names to their implementation functions
_operator_registry: dict[str, Callable[[Any, Any], bool]] = {}
# Mapping of transform names to their implementation functions
_transform_registry: dict[str, Callable[..., Any]] = {}


def register_operator(name: str):
    """
    Decorator to register a new operator under the given name.
    The decorated function must accept (value, operand) and return bool.
    """
    def decorator(fn: Callable[[Any, Any], bool]):
        if name in _operator_registry:
            logger.warning(f"Operator '{name}' is already registered. Overwriting.")
        _operator_registry[name] = fn
        logger.debug(f"Registered operator: {name}")
        return fn

    return decorator


def register_transform(name: str):
    """
    Decorator to register a new transform under the given name.
    The decorated function can accept any arguments and return any value.
    """
    def decorator(fn: Callable[..., Any]):
        if name in _transform_registry:
            logger.warning(f"Transform '{name}' is already registered. Overwriting.")
        _transform_registry[name] = fn
        logger.debug(f"Registered transform: {name}")
        return fn

    return decorator


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
