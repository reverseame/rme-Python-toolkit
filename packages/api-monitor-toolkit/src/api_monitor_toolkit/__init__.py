import typer
from common.logger import get_logger

from api_monitor_toolkit.commands.analyzer import analyzer as analyzer_command
from api_monitor_toolkit.commands.spider import spider as spider_command

logger = get_logger(__name__)
app = typer.Typer(no_args_is_help=True, pretty_exceptions_show_locals=False)

app.command()(analyzer_command)
app.command()(spider_command)

if __name__ == "__main__":
    app()
