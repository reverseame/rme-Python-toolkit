from typing import Any, Callable

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
        _operator_registry[name] = fn
        return fn

    return decorator


def register_transform(name: str):
    """
    Decorator to register a new transform under the given name.
    The decorated function can accept any arguments and return any value.
    """

    def decorator(fn: Callable[..., Any]):
        _transform_registry[name] = fn
        return fn

    return decorator


# ---------------------------------------------------------------------
# Auto-load of operators module:
# Ensure that all @register_operator decorators in operators.py
# are executed when this registry is imported.
# ---------------------------------------------------------------------
try:
    from ioc_extractor.rules.operators import *  # noqa: F403
except ImportError:
    # If operators.py is missing or fails to load, ignore and proceed.
    pass
