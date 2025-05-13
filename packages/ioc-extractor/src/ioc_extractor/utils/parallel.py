# parallel.py (run_pipeline actualizado para usar print_match)

import json
import os
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
from ioc_extractor.utils.logger import get_logger

logger = get_logger(__name__)

def detect_workers(requested: int = None) -> int:
    cpu = os.cpu_count() or 1
    load = os.getloadavg()[0]
    available_threads = max(1, cpu - int(load))
    result = requested if requested and requested > 0 else available_threads
    logger.info(f"Detected {result} worker(s) (CPU={cpu}, Load={load:.2f})")
    return result

def sample_entries(path: str, count: int = 50) -> list[dict[str, Any]]:
    logger.debug(f"Sampling up to {count} entries from file: {path}")
    batch: list[dict[str, Any]] = []
    try:
        with open(path, encoding="latin-1") as f:
            for entry in ijson.items(f, "item"):
                batch.append(entry)
                if len(batch) >= count:
                    break
    except Exception as e:
        logger.error(f"Failed to sample entries from {path}: {e}", exc_info=True)
    return batch

def compute_chunk_size(
    path: str,
    rules: list[dict[str, Any]],
    sample_count: int = 50,
    target_secs: float = 1.0,
    min_size: int = 500,
) -> int:
    logger.info(f"Computing optimal chunk size for file: '{path}'")
    samples = sample_entries(path, sample_count)
    if not samples:
        logger.warning(f"No samples found in file: {path}, using min size {min_size}")
        return min_size

    try:
        start = time.time()
        for entry in samples:
            for rule in rules:
                execute_rule(entry, rule)
        elapsed = time.time() - start
        per_entry = elapsed / len(samples)
        mem = psutil.virtual_memory()
        mem_factor = max(0.5, min(mem.available / (1024**3) / 2, 2))
        size = int((target_secs / per_entry) * mem_factor)
        final_size = max(min_size, size)
        logger.info(f"Estimated chunk size for '{path}': {final_size}")
        return final_size
    except Exception as e:
        logger.error(f"Error computing chunk size for {path}: {e}", exc_info=True)
        return min_size

def worker_task(batch: list[dict[str, Any]], rules: list[dict[str, Any]]) -> tuple[dict[str, int], list[dict[str, Any]]]:
    local_counts: dict[str, int] = defaultdict(int)
    local_matches: list[dict[str, Any]] = []
    for entry in batch:
        for rule in rules:
            result = execute_rule(entry, rule)
            if result:
                rule_name = rule.get("name", "unnamed")
                local_counts[rule_name] += 1
                local_matches.append(result)
                break
    return local_counts, local_matches

def start_producer(inputs: list[str], chunk_sizes: dict[str, int], task_queue: Queue, workers: int) -> None:
    def producer():
        try:
            for infile in inputs:
                file_hash = file_sha256(infile)
                cs = chunk_sizes[infile]
                logger.debug(f"Producing chunks from {infile} with chunk size {cs}")
                for batch in read_json_chunks(infile, cs):
                    task_queue.put((infile, file_hash, batch, str(infile)))
            for _ in range(workers):
                task_queue.put(None)
        except Exception as e:
            logger.error(f"Error in producer thread: {e}", exc_info=True)

    Thread(target=producer, daemon=True).start()

def run_pipeline(
    inputs: list[str],
    chunk_sizes: dict[str, int],
    workers: int,
    rules: list[dict[str, Any]],
    output_path: str = None,
    verbose: bool = False,
) -> tuple[dict[str, int], list[dict[str, Any]]]:
    logger.debug("Starting pipeline execution...")
    task_queue: Queue = Queue(maxsize=workers * 2)
    start_producer(inputs, chunk_sizes, task_queue, workers)

    agg_counts: dict[str, int] = defaultdict(int)
    temp_output = None
    first_written = False
    matches: list[dict[str, Any]] = []

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

        for _ in range(workers):
            task = task_queue.get()
            if task is None:
                break
            infile, file_hash, batch, source_file = task
            future = executor.submit(worker_task, batch, rules)
            pending.append((future, source_file))

        while pending:
            done_set, _ = wait([f[0] for f in pending], return_when=FIRST_COMPLETED)
            for future_obj in list(done_set):
                future_tuple = next(p for p in pending if p[0] == future_obj)
                pending.remove(future_tuple)
                future, source_file = future_tuple

                try:
                    counts, chunk_matches = future.result()
                except Exception as e:
                    logger.warning(f"Worker task failed: {e}", exc_info=True)
                    continue

                for rule_name, cnt in counts.items():
                    agg_counts[rule_name] += cnt

                for match in chunk_matches:
                    print_match(
                        match_type=rule_name,
                        match_id=match.get("id", "?"),
                        api=match.get("api", "?"),
                        source_file=source_file,
                        selected_fields=match.get("fields", {})
                    )
                    if temp_output:
                        if first_written:
                            temp_output.write(",\n")
                        temp_output.write(json.dumps(match, ensure_ascii=False))
                        first_written = True
                    else:
                        matches.append(match)

                task = task_queue.get()
                if task is None:
                    continue
                infile, file_hash, batch, source_file = task
                future = executor.submit(worker_task, batch, rules)
                pending.append((future, source_file))

    if temp_output:
        temp_output.write("]\n")
        temp_output.close()
        logger.info(f"Finished writing output to {output_path}")
        return agg_counts, []

    logger.info("Pipeline execution completed")
    return agg_counts, matches
