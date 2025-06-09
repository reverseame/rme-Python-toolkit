import json
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests
from common.logger import get_logger
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = get_logger(__name__)


def choose_output_handler(output: Optional[str]) -> "OutputHandler":
    if not output:
        return StdoutHandler()
    scheme = urlparse(output).scheme
    if scheme in ("http", "https"):
        return HTTPPostHandler(output)
    return JSONLinesOutputHandler(Path(output))


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


class JSONLinesOutputHandler(OutputHandler):
    def __init__(self, path: Path):
        self.path = path
        self.file = None
        self.first = True

    def start(self):
        try:
            self.file = open(self.path, "w", encoding="utf-8")
            self.file.write("[\n")
        except OSError as e:
            logger.error(f"Failed to open {self.path}: {e}")
            raise

    def write(self, entry: dict):
        if self.file is None:
            raise RuntimeError("Output file not open.")
        prefix = "" if self.first else ",\n"
        self.file.write(f"{prefix}{json.dumps(entry, ensure_ascii=False)}")
        if self.first:
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
        if self.session is None:
            self.start()
        try:
            resp = self.session.post(self.url, json=entry)
            if resp.status_code >= 400:
                logger.warning(f"HTTP POST failed: {resp.status_code}")
        except requests.RequestException as e:
            logger.warning(f"HTTP POST error: {e}")

    def finish(self):
        if self.session:
            self.session.close()
            self.session = None
