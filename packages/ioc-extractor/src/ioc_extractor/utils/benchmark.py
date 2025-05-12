import os
import time
from statistics import mean, stdev
from typing import Any

import ijson
from ioc_extractor.core.processor import file_sha256, process_chunk
from ioc_extractor.utils.parallel import sample_entries
from rich.console import Console
from rich.table import Table


def count_entries(path: str, sample_size: int = 1000) -> int:
    sample = sample_entries(path, count=sample_size)
    if not sample:
        return 0
    avg_entry_size = sum(len(str(e)) for e in sample) / len(sample)
    file_size = os.path.getsize(path)
    return int(file_size / avg_entry_size)


def benchmark_pipeline(
    inputs: list[str],
    rules: list[dict[str, Any]],
    thread_options: list[int],
    chunk_options: list[int],
    sample_count: int = 20000,
) -> tuple[int, dict[str, int]]:
    """
    Run benchmark on each input file using various (threads, chunk_size) combinations.
    Return the best thread count and a dict of optimal chunk sizes per file.
    """
    console = Console()
    console.print("[*] Starting benchmark...")
    best_threads = thread_options[0]
    best_global_time = float("inf")
    chunk_sizes: dict[str, int] = {}
    summary: list[tuple[str, int, float, float, float, float, float]] = []
    # file, best_chunk, mean, std, best_time, speed, size_mb

    for path in inputs:
        times: dict[tuple[int, int], float] = {}
        best_time = float("inf")
        best_chunk = chunk_options[0]

        file_hash = file_sha256(path)
        sample = []
        sample_bytes = 0
        with open(path, encoding="latin-1") as f:
            start_offset = f.tell()
            for entry in ijson.items(f, "item"):
                sample.append(entry)
                if len(sample) >= sample_count:
                    break
            end_offset = f.tell()
            sample_bytes = end_offset - start_offset

        for t in thread_options:
            for c in chunk_options:
                start = time.perf_counter()
                chunks = [sample[i : i + c] for i in range(0, len(sample), c)]
                for chunk in chunks:
                    process_chunk(path, file_hash, chunk, rules)
                elapsed = time.perf_counter() - start
                times[(t, c)] = elapsed

                if 0.01 < elapsed < best_time:
                    best_time = elapsed
                    best_chunk = c
                if 0.01 < elapsed < best_global_time:
                    best_global_time = elapsed
                    best_threads = t

        file_size_bytes = os.path.getsize(path)
        file_size_mb = file_size_bytes / (1024 * 1024)
        chosen_time = times.get((best_threads, best_chunk), best_time)
        speed = (sample_bytes / 1024 / 1024) / chosen_time if chosen_time > 0 else 0.0

        m = mean(times.values())
        s = stdev(times.values()) if len(times) > 1 else 0.0
        chunk_sizes[path] = best_chunk
        summary.append(
            (os.path.basename(path), best_chunk, m, s, chosen_time, speed, file_size_mb)
        )

    table = Table(title=f"Benchmark Summary (sample size: {sample_count})")
    table.add_column("File", style="cyan", no_wrap=True)
    table.add_column("Size (MB)", justify="right")
    table.add_column("Best Chunk", justify="right")
    table.add_column("Mean (s)", justify="right")
    table.add_column("StdDev (s)", justify="right")
    table.add_column("Best Time (s)", justify="right")
    table.add_column("Speed (MB/s)", justify="right")

    for file, best_chunk, avg, std, best, speed, size_mb in summary:
        table.add_row(
            file,
            f"{size_mb:.1f}",
            str(best_chunk),
            f"{avg:.3f}",
            f"{std:.3f}",
            f"{best:.3f}",
            f"{speed:.1f}",
        )

    console.print(table)
    console.print(f"\n[*] Best global thread count: {best_threads}")
    return best_threads, chunk_sizes
