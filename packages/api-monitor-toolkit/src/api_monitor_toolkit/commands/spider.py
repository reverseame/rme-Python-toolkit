from typing import Annotated

import typer
from api_monitor_toolkit.output.handler import get_output_handler
from api_monitor_toolkit.services.spider_controller import SpiderController
from common.callbacks import verbose_callback
from common.logger import get_logger

logger = get_logger(__name__)
app = typer.Typer()


@app.command()
def spider(
    parameters: Annotated[bool, typer.Option("-p", "--parameters")] = False,
    call_stack: Annotated[bool, typer.Option("-c", "--call-stack")] = False,
    output: Annotated[str, typer.Option("-o", "--output")] = None,
    verbosity: Annotated[
        int,
        typer.Option(
            "-v",
            "--verbose",
            count=True,
            callback=verbose_callback,
            help="Increase logging verbosity",
        ),
    ] = 0,
):
    """
    Extract information from API Monitor's UI tree view (previously captured trace).
    """
    logger.info("Starting spider...")

    handler = get_output_handler(output)
    controller = SpiderController(
        include_params=parameters,
        include_stack=call_stack,
        output=handler,
    )

    try:
        controller.run()
        logger.info("Spider completed successfully.")
    except Exception as e:
        logger.exception(f"Spider failed: {e}")
