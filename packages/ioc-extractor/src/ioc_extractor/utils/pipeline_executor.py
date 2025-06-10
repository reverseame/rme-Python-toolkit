import json
import time
from collections import defaultdict
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from queue import Queue
from threading import Thread
from typing import Any

import ijson
import psutil
from ioc_extractor.engine.executor import execute_rule
from ioc_extractor.utils.formatter import print_match
from ioc_extractor.utils.io import file_sha256, read_json_chunks
from common.logger import get_logger

logger = get_logger(__name__)

def compute_chunk_size(
    path: str,
    rules: list[dict[str, Any]],
    sample_count: int = 50,
    target_secs: float = 1.0,
    min_size: int = 500,
    target_ram_mb: int = 2048,
) -> int:
    """Estimate chunk size using sample processing time and available RAM."""
    logger.info(f"Computing optimal chunk size for file: '{path}'")
    samples = sample_entries(path, sample_count)
    if not samples:
        logger.warning(f"No samples found in file: {path}, using min size {min_size}")
        return min_size

    try:
        start = time.time()
        for entry in samples:
            for rule in rules:
                execute_rule(entry, rule, source_file=path)
        elapsed = time.time() - start
        per_entry = elapsed / len(samples)
        mem = psutil.virtual_memory()
        ram_limit = max(256, min(target_ram_mb, mem.available / (1024**2)))
        size = int((target_secs / per_entry) * (ram_limit / 128))
        return max(min_size, size)
    except Exception as e:
        logger.error(f"Error computing chunk size for {path}: {e}", exc_info=True)
        return min_size

def sample_entries(path: str, count: int = 50) -> list[dict[str, Any]]:
    """Read up to `count` entries from a JSON array."""
    logger.debug(f"Sampling up to {count} entries from file: {path}")
    batch = []
    try:
        with open(path, encoding="latin-1") as f:
            for entry in ijson.items(f, "item"):
                batch.append(entry)
                if len(batch) >= count:
                    break
    except Exception as e:
        logger.error(f"Failed to sample entries from {path}: {e}", exc_info=True)
    return batch

def worker_task(batch: list[dict], rules: list[dict], source_file: str) -> tuple[dict[str, int], list[dict]]:
    """Apply all rules to a batch and return match counts and results."""
    local_counts = defaultdict(int)
    local_matches = []
    for entry in batch:
        for rule in rules:
            result = execute_rule(entry, rule, source_file)
            if result:
                rule_name = result["rule"]["name"]
                local_counts[rule_name] += 1
                local_matches.append(result)
                break
    return local_counts, local_matches

def start_producer(inputs: list[str], chunk_sizes: dict[str, int], task_queue: Queue, workers: int) -> None:
    """Start a background thread to feed chunks to the processing queue."""
    def producer():
        try:
            for infile in inputs:
                file_hash = file_sha256(infile)
                cs = chunk_sizes[infile]
                logger.debug(f"Producing chunks from {infile} with chunk size {cs}")
                for batch in read_json_chunks(infile, cs):
                    task_queue.put((infile, file_hash, batch, infile))
            for _ in range(workers):
                task_queue.put(None)
        except Exception as e:
            logger.error(f"Error in producer thread: {e}", exc_info=True)

    Thread(target=producer, daemon=True).start()

def handle_completed_task(
    future, source_file, agg_counts, matches, temp_output, first_written
) -> bool:
    """Process the result of a completed worker task."""
    try:
        counts, chunk_matches = future.result()
    except Exception as e:
        logger.warning(f"Worker task failed: {e}", exc_info=True)
        return first_written

    for rule_name, cnt in counts.items():
        agg_counts[rule_name] += cnt

    for match in chunk_matches:
        print_match(
            match_type=match["rule"].get("name", "unnamed") + ("::" + match["rule"]["variant"] if match["rule"].get("variant") else ""),
            api=match.get("api", "?"),
            source_file=match.get("sources", {}).get("input", "?"),
            selected_fields=match.get("attributes", {})
        )

        if temp_output:
            if first_written:
                temp_output.write(",\n")
            temp_output.write(json.dumps(match, ensure_ascii=False))
            first_written = True
        else:
            matches.append(match)

    return first_written

def run_pipeline(
    inputs: list[str],
    chunk_sizes: dict[str, int],
    workers: int,
    rules: list[dict[str, Any]],
    output_path: str = None,
    verbose: bool = False,
) -> tuple[dict[str, int], list[dict[str, Any]]]:
    """Orchestrates rule execution across inputs with multiprocessing."""
    logger.debug("Starting pipeline execution...")
    task_queue: Queue = Queue(maxsize=workers * 2)
    start_producer(inputs, chunk_sizes, task_queue, workers)

    agg_counts = defaultdict(int)
    matches = []
    temp_output = None
    first_written = False

    if output_path:
        try:
            temp_output = open(output_path, "w", encoding="utf-8")
            temp_output.write("[")
            logger.info(f"Writing results to {output_path}")
        except Exception as e:
            logger.error(f"Failed to open output file '{output_path}': {e}", exc_info=True)
            temp_output = None

    with ProcessPoolExecutor(max_workers=workers) as executor:
        pending = []

        # Initial task submission
        for _ in range(workers):
            task = task_queue.get()
            if task is None:
                break
            infile, file_hash, batch, source_file = task
            future = executor.submit(worker_task, batch, rules, source_file)
            pending.append((future, source_file))

        # Process task results and refill queue
        while pending:
            done_set, _ = wait([f[0] for f in pending], return_when=FIRST_COMPLETED)
            for future_obj in list(done_set):
                future_tuple = next(p for p in pending if p[0] == future_obj)
                pending.remove(future_tuple)
                future, source_file = future_tuple
                first_written = handle_completed_task(
                    future, source_file, agg_counts, matches, temp_output, first_written
                )

                task = task_queue.get()
                if task is None:
                    continue
                infile, file_hash, batch, source_file = task
                future = executor.submit(worker_task, batch, rules, source_file)
                pending.append((future, source_file))

    if temp_output:
        temp_output.write("]\n")
        temp_output.close()
        logger.info(f"Finished writing output to {output_path}")
        return agg_counts, []

    logger.info("Pipeline execution completed")
    return agg_counts, matches
