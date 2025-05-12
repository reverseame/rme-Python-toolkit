import os
import time
from collections import defaultdict
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from queue import Queue
from threading import Thread
from typing import Any

import ijson
import psutil
from ioc_extractor.core.processor import chunked_entries, file_sha256, process_chunk


def detect_workers(requested: int = None) -> int:
    cpu = os.cpu_count() or 1
    load = os.getloadavg()[0]
    available_threads = max(1, cpu - int(load))
    return requested if requested and requested > 0 else available_threads


def sample_entries(path: str, count: int = 50) -> list[dict[str, Any]]:
    batch: list[dict[str, Any]] = []
    with open(path, encoding="latin-1") as f:
        for entry in ijson.items(f, "item"):
            batch.append(entry)
            if len(batch) >= count:
                break
    return batch


def compute_chunk_size(
    path: str,
    rules: list[dict[str, Any]],
    sample_count: int = 50,
    target_secs: float = 1.0,
    min_size: int = 500,
) -> int:
    samples = sample_entries(path, sample_count)
    if not samples:
        return min_size

    file_hash = file_sha256(path)
    start = time.time()
    process_chunk(path, file_hash, samples, rules)
    elapsed = time.time() - start
    per_entry = elapsed / len(samples) if samples else 0.01

    mem = psutil.virtual_memory()
    mem_factor = max(0.5, min(mem.available / (1024**3) / 2, 2))

    size = int((target_secs / per_entry) * mem_factor)
    return max(min_size, size)


def run_pipeline(
    inputs: list[str],
    chunk_sizes: dict[str, int],
    workers: int,
    rules: list[dict[str, Any]],
    output_path: str = None,
    verbose: bool = False,
) -> tuple[dict[str, int], list[dict[str, Any]]]:
    task_queue: Queue = Queue(maxsize=workers * 2)

    def producer():
        for infile in inputs:
            file_hash = file_sha256(infile)
            cs = chunk_sizes[infile]
            for batch in chunked_entries(infile, cs):
                task_queue.put((infile, file_hash, batch))
        for _ in range(workers):
            task_queue.put(None)

    Thread(target=producer, daemon=True).start()

    agg_counts: dict[str, int] = defaultdict(int)
    temp_output = None
    if output_path:
        temp_output = open(output_path, "w", encoding="utf-8")
        temp_output.write("[")
        first_written = False

    with ProcessPoolExecutor(max_workers=workers) as executor:
        pending = []
        for _ in range(workers):
            task = task_queue.get()
            if task is None:
                break
            infile, file_hash, batch = task
            pending.append(
                executor.submit(process_chunk, infile, file_hash, batch, rules, verbose)
            )

        while pending:
            done_set, _ = wait(pending, return_when=FIRST_COMPLETED)
            future = done_set.pop()
            pending.remove(future)
            counts, matches = future.result()
            for rule_name, cnt in counts.items():
                agg_counts[rule_name] += cnt

            if temp_output:
                import json

                for match in matches:
                    if first_written:
                        temp_output.write(",\n")
                    temp_output.write(json.dumps(match, ensure_ascii=False))
                    first_written = True

            task = task_queue.get()
            if task is None:
                continue
            infile, file_hash, batch = task
            pending.append(
                executor.submit(process_chunk, infile, file_hash, batch, rules, verbose)
            )

    if temp_output:
        temp_output.write("]\n")
        temp_output.close()
        return agg_counts, []

    return agg_counts, []
