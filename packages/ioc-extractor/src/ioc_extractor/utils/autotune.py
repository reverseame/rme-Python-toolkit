import time
from itertools import product
from typing import Any

import ijson
from ioc_extractor.engine.executor import execute_rule
from more_itertools import chunked


def simulate_execution(
    sample: list[dict[str, Any]],
    chunk_size: int,
    rules: list[dict[str, Any]],
    source_file: str
) -> float:
    """Run all rules over the sample split into chunks. Returns elapsed time."""
    chunks = list(chunked(sample, chunk_size))
    start = time.perf_counter()
    for chunk in chunks:
        for entry in chunk:
            for rule in rules:
                execute_rule(entry, rule, source_file)
    return time.perf_counter() - start


def load_sample(
    path: str,
    limit: int = 20000
) -> list[dict[str, Any]]:
    """Load up to `limit` entries from a JSON file using ijson."""
    sample = []
    with open(path, encoding="latin-1") as f:
        for entry in ijson.items(f, "item"):
            sample.append(entry)
            if len(sample) >= limit:
                break
    return sample


def auto_tune_resources(
    inputs: list[str],
    rules: list[dict[str, Any]],
    thread_candidates: list[int],
    chunk_candidates: list[int],
    sample_size: int = 20000,
) -> tuple[int, dict[str, int]]:
    """Benchmark inputs to find the best thread count and chunk size per file."""
    best_threads = thread_candidates[0]
    best_global_time = float("inf")
    chunk_sizes: dict[str, int] = {}

    for path in inputs:
        best_time = float("inf")
        best_chunk = chunk_candidates[0]
        sample = load_sample(path, limit=sample_size)

        for threads, chunk_size in product(thread_candidates, chunk_candidates):
            elapsed = simulate_execution(sample, chunk_size, rules, source_file=path)
            if 0.01 < elapsed < best_time:
                best_time = elapsed
                best_chunk = chunk_size
            if 0.01 < elapsed < best_global_time:
                best_global_time = elapsed
                best_threads = threads

        chunk_sizes[path] = best_chunk

    return best_threads, chunk_sizes
