import typer

from api_monitor_toolkit.commands.spider import spider as spider_command
from api_monitor_toolkit.utils.logger import get_logger

logger = get_logger(__name__)
app = typer.Typer(no_args_is_help=True, pretty_exceptions_show_locals=False)

app.command()(spider_command)

if __name__ == "__main__":
    app()
