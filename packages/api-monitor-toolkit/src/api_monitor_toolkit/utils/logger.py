import logging

from rich.logging import RichHandler


def configure_logger(verbosity: int):
    """Configure root logger with rich formatting and verbosity control."""
    levels = [logging.WARNING, logging.INFO, logging.DEBUG]
    level = levels[min(verbosity, len(levels) - 1)]

    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, markup=True)],
    )

def get_logger(name: str) -> logging.Logger:
    """Return a logger scoped to the given module name."""
    return logging.getLogger(name)
