import hashlib
from collections import defaultdict
from collections.abc import Iterator
from os.path import basename
from typing import Any

import ijson
from ioc_extractor.rules.engine import execute_rule
from ioc_extractor.rules.formatter import print_match
from ioc_extractor.utils.logger import get_logger

logger = get_logger(__name__)

def file_sha256(path: str) -> str:
    """
    Compute SHA-256 hash of the file at the given path.
    """
    logger.debug(f"Computing SHA-256 for file: '{path}'")
    sha256 = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        digest = sha256.hexdigest()
        logger.debug(f"SHA-256 for {path}: {digest[0:6]}...{digest[-6:]}")
        return digest
    except Exception as e:
        logger.error(f"Failed to compute SHA-256 for '{path}': {e}", exc_info=True)
        raise

def chunked_entries(file_path: str, chunk_size: int) -> Iterator[list[dict[str, Any]]]:
    """
    Yield successive chunks of entries from the top-level JSON array.
    """
    logger.info(f"Reading JSON entries in chunks from '{file_path}' (chunk size: {chunk_size})")
    try:
        with open(file_path, encoding="latin-1") as f:
            batch: list[dict[str, Any]] = []
            for entry in ijson.items(f, "item"):
                batch.append(entry)
                if len(batch) >= chunk_size:
                    logger.debug(f"Yielding a chunk of {len(batch)} entries from '{file_path}'")
                    yield batch
                    batch = []
            if batch:
                logger.debug(f"Yielding final chunk of {len(batch)} entries from '{file_path}'")
                yield batch
    except Exception as e:
        logger.error(f"Error while reading and chunking file '{file_path}': {e}", exc_info=True)
        raise

def process_chunk(
    file_path: str,
    file_hash: str,
    entries: list[dict[str, Any]],
    rules: list[dict[str, Any]],
) -> tuple[dict[str, int], list[dict[str, Any]]]:
    """
    Process a chunk of entries and apply rules to detect matches.
    """
    logger.debug(f"Processing chunk from file: '{file_path}' (hash: {file_hash[0:6]}...{file_hash[-6:]}), {len(entries)} entries")
    counts: dict[str, int] = defaultdict(int)
    matches: list[dict[str, Any]] = []

    for entry_index, entry in enumerate(entries):
        for rule in rules:
            try:
                selected_data = execute_rule(entry, rule)
            except Exception as e:
                logger.warning(f"Rule execution failed on entry index {entry_index} with rule '{rule.get('name')}'. Error: {e}", exc_info=True)
                continue

            if selected_data:
                counts[rule["name"]] += 1

                api = selected_data["api"].split("(")[0].strip()
                source_file = basename(file_path)
                match_info = {
                    "id": selected_data["id"],
                    "api": api,
                    "type": rule["name"],
                    "fields": selected_data["fields"],
                    "source": {"file_name": source_file, "sha256": file_hash},
                }
                matches.append(match_info)

                logger.debug(f"Match found in file '{source_file}': rule={rule['name']}, id={selected_data['id']}")
                print_match(
                    match_type=rule["name"],
                    match_id=selected_data["id"],
                    api=api,
                    source_file=source_file,
                    selected_fields=selected_data["fields"],
                )
                break  # Stop at first matching rule

    logger.info(f"Chunk processing completed: {sum(counts.values())} matches found in '{file_path}'")
    return counts, matches
