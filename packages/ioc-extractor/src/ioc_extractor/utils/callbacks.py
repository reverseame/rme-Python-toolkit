import typer
from ioc_extractor.utils.logger import configure_logger


def verbose_callback(ctx: typer.Context, param: typer.CallbackParam, value: int):
    if ctx.resilient_parsing:
        return

    configure_logger(value)
    return value
