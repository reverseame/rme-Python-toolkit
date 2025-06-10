import typer

from ioc_extractor.commands.analyzer import analyze as analyze_cmd
from ioc_extractor.commands.visualizer import visualize as visualize_cmd

app = typer.Typer(no_args_is_help=True, pretty_exceptions_show_locals=False)

app.command()(analyze_cmd)
app.command()(visualize_cmd)

if __name__ == "__main__":
    app()
