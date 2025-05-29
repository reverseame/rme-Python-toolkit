import json
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional
from pathlib import Path
from urllib.parse import urlparse
from api_monitor_toolkit.utils.logger import get_logger

logger = get_logger(__name__)

def choose_output_handler(output: Optional[str]) -> "OutputHandler":
    if output is None:
        return StdoutHandler()
    parsed = urlparse(output)
    if parsed.scheme in ("http", "https"):
        return HTTPPostHandler(output)
    else:
        return JSONFileHandler(Path(output))

class OutputHandler:
    def start(self):
        pass
    def write(self, entry: dict):
        pass
    def finish(self):
        pass

class StdoutHandler(OutputHandler):
    def start(self):
        pass
    def write(self, entry: dict):
        print(json.dumps(entry, indent=2), end="")
    def finish(self):
        pass

class JSONFileHandler(OutputHandler):
    def __init__(self, path: Path):
        self.path = path
        self.file = open(path, "w", encoding="utf-8")
        self.first = True

    def start(self):
        self.file.write("[\n")

    def write(self, entry: dict):
        if not self.first:
            self.file.write(",\n")
        else:
            self.first = False
        self.file.write(json.dumps(entry, indent=2))

    def finish(self):
        self.file.write("\n]\n")
        self.file.close()
        logger.info(f"Output saved to {Path(self.path).resolve()}")

class HTTPPostHandler(OutputHandler):
    def __init__(self, url: str):
        self.url = url
        self.session = None

    def start(self):
        self.session = requests.Session()
        # Desactivar retries automáticos
        adapter = HTTPAdapter(max_retries=Retry(total=0))
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def write(self, entry: dict):
        if not self.session:
            self.start()
        try:
            response = self.session.post(self.url, json=entry)
            if response.status_code >= 400:
                logger.warning(f"HTTP POST failed with status {response.status_code}")
        except Exception as e:
            logger.warning(f"HTTP POST exception: {e}")

    def finish(self):
        if self.session:
            self.session.close()
            self.session = None
