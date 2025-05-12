from rich.console import Console
from rich.text import Text

console = Console()


def log(message: str, level: str = "info") -> None:
    styles = {
        "info": "white",
        "success": "green",
        "warning": "yellow",
        "error": "bold red",
        "debug": "dim",
    }

    style = styles.get(level, "white")
    text = Text()
    text.append(f"{message}", style=style)
    console.print(text)
