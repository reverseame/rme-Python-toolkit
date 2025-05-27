from pathlib import Path
from typing import Annotated

import typer
from ioc_extractor.utils.callbacks import verbose_callback
from ioc_extractor.utils.graph_server import serve_graph
from ioc_extractor.utils.logger import get_logger

logger = get_logger(__name__)
app = typer.Typer()

def visualize(
    input: Annotated[Path, typer.Option("-i", "--input", help="Path to the result JSON file")],
    verbose: Annotated[int, typer.Option("-v", "--verbose", count=True, callback=verbose_callback)] = 0
):
    """Launch interactive graph viewer for the given analysis output."""
    serve_graph(input_file=str(input))
