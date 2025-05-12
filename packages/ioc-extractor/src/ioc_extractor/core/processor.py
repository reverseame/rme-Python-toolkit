import hashlib
from collections import defaultdict
from collections.abc import Iterator
from os.path import basename
from typing import Any

import ijson
from ioc_extractor.rules.engine import execute_rule
from ioc_extractor.rules.formatter import print_match


def file_sha256(path: str) -> str:
    """
    Compute SHA-256 hash of the file at the given path.
    """
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def chunked_entries(file_path: str, chunk_size: int) -> Iterator[list[dict[str, Any]]]:
    """
    Yield successive chunks of entries from the top-level JSON array.
    """
    with open(file_path, encoding="latin-1") as f:
        batch: list[dict[str, Any]] = []
        for entry in ijson.items(f, "item"):
            batch.append(entry)
            if len(batch) >= chunk_size:
                yield batch
                batch = []
        if batch:
            yield batch


def process_chunk(
    file_path: str,
    file_hash: str,
    entries: list[dict[str, Any]],
    rules: list[dict[str, Any]],
    verbose: bool = False,
) -> tuple[dict[str, int], list[dict[str, Any]]]:
    """
    Process a chunk of entries:
      - file_path and file_hash for source metadata
      - entries: list of JSON objects
      - rules: detection rules

    Returns counts and list of matches with source info.
    """
    counts: dict[str, int] = defaultdict(int)
    matches: list[dict[str, Any]] = []

    for entry in entries:
        for rule in rules:
            selected_data = execute_rule(entry, rule)
            if selected_data:
                counts[rule["name"]] += 1

                api = selected_data["api"].split("(")[0].strip()
                source_file = basename(file_path)
                matches.append(
                    {
                        "id": selected_data["id"],
                        "api": api,
                        "type": rule["name"],
                        "fields": selected_data["fields"],
                        "source": {"file_name": source_file, "sha256": file_hash},
                    }
                )
                if verbose:
                    print_match(
                        match_type=rule["name"],
                        match_id=selected_data["id"],
                        api=api,
                        source_file=source_file,
                        selected_fields=selected_data["fields"],
                    )
                break

    return counts, matches
