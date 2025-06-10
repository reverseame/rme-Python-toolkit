import json
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from api_monitor_toolkit.core.exceptions import OutputHandlerError
from common.logger import get_logger

logger = get_logger(__name__)


def get_output_handler(target: Optional[str]) -> "OutputHandler":
    if not target:
        return StdoutHandler()
    scheme = urlparse(target).scheme
    if scheme in ("http", "https"):
        return HTTPPostHandler(target)
    return JSONLinesHandler(Path(target))


class OutputHandler:
    def start(self):
        pass

    def write(self, entry: dict):
        raise NotImplementedError

    def finish(self):
        pass


class StdoutHandler(OutputHandler):
    def write(self, entry: dict):
        print(json.dumps(entry, ensure_ascii=False))


class JSONLinesHandler(OutputHandler):
    def __init__(self, path: Path):
        self.path = path
        self.file = None
        self.first = True

    def start(self):
        try:
            self.file = self.path.open("w", encoding="utf-8")
            self.file.write("[\n")
        except Exception as e:
            raise OutputHandlerError(f"Failed to open output file: {e}")

    def write(self, entry: dict):
        if not self.file:
            raise OutputHandlerError("Output file not open.")
        prefix = "" if self.first else ",\n"
        self.file.write(f"{prefix}{json.dumps(entry, ensure_ascii=False)}")
        self.first = False

    def finish(self):
        if self.file:
            self.file.write("\n]\n")
            self.file.close()


class HTTPPostHandler(OutputHandler):
    def __init__(self, url: str):
        self.url = url
        self.session = None

    def start(self):
        self.session = requests.Session()
        adapter = HTTPAdapter(max_retries=Retry(total=0))
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def write(self, entry: dict):
        if not self.session:
            self.start()
        try:
            response = self.session.post(self.url, json=entry)
            if response.status_code >= 400:
                logger.warning(f"HTTP POST failed: {response.status_code}")
        except requests.RequestException as e:
            logger.warning(f"HTTP POST error: {e}")

    def finish(self):
        if self.session:
            self.session.close()
