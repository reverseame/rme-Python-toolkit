# __init__.py (modificado con logs)
import os
from pathlib import Path
from typing import Annotated, Optional

import typer

from ioc_extractor.rules.query_loader import DEFAULT_PATTERNS_URL, load_query_rules
from ioc_extractor.utils.benchmark import benchmark_pipeline
from ioc_extractor.utils.callbacks import verbose_callback
from ioc_extractor.utils.logger import get_logger
from ioc_extractor.utils.parallel import (
    compute_chunk_size,
    detect_workers,
    run_pipeline,
)
from ioc_extractor.utils.perf import monitor_wrapper

logger = get_logger(__name__)
app = typer.Typer()

@app.command()
def main(
    input: Annotated[list[Path], typer.Option("-i", "--input", show_default=False, help="One or more input JSON files to process")],
    patterns: Annotated[str, typer.Option("-p", "--patterns", show_default=False, help="Local path or URL to patterns JSON file.")] = DEFAULT_PATTERNS_URL,
    output: Annotated[Optional[Path], typer.Option("-o", "--output", show_default=False, help="Output file to save aggregated results (JSON format)")] = None,
    threads: Annotated[int, typer.Option("-t", "--threads", help="Number of worker processes")] = os.cpu_count(),
    chunk_size: Annotated[int, typer.Option(show_default=False, help="Number of JSON objects per chunk")] = None,
    benchmark: Annotated[bool, typer.Option(help="Run benchmark mode to auto-tune threads and chunk size.")] = False,
    benchmark_sample_size: Annotated[int, typer.Option(help="Number of entries to use for benchmark mode.")] = 20000,
    dry_run: Annotated[bool, typer.Option(help="Run only the benchmark phase without processing the full dataset.")] = False,
    monitoring: Annotated[bool, typer.Option(help="Enable performance statistics")] = False,
    verbose: Annotated[int, typer.Option("--verbose", "-v", count=True, callback=verbose_callback)] = 0,
):
    rules = load_query_rules(patterns)
    chunk_sizes: dict[str, int] = {}

    if benchmark:
        logger.info("Benchmark mode enabled")
        thread_opts = [max(1, os.cpu_count() // 2), os.cpu_count(), os.cpu_count() * 2]
        chunk_opts = [500, 1000, 2000, 4000]
        sample_size = benchmark_sample_size or 20000

        logger.info(f"Running benchmark with sample size: {sample_size}")
        best_threads, best_chunks = benchmark_pipeline(input, rules, thread_opts, chunk_opts, sample_count=sample_size)
        threads = best_threads
        chunk_sizes = best_chunks
        logger.info(f"Best configuration - Threads: {threads}, Chunk sizes: {chunk_sizes}")

        if dry_run:
            logger.info("Dry run complete. Exiting after benchmark.")
            raise typer.Exit()

    else:
        for infile in input:
            if chunk_size:
                cs = chunk_size
                logger.info(f"Using specified chunk size {cs} for {infile}")
            else:
                logger.info(f"Estimating chunk size for '{infile}'")
                cs = compute_chunk_size(infile, rules)
            chunk_sizes[infile] = cs
            logger.info(f"Chunk size for '{infile}': {cs}")

    workers = detect_workers(threads)
    logger.info(f"Using {workers} worker(s) for parallel processing")

    @monitor_wrapper(enabled=monitoring)
    def run():
        counts, _ = run_pipeline(
            inputs=input,
            chunk_sizes=chunk_sizes,
            workers=workers,
            rules=rules,
            output_path=output,
        )

        total = sum(counts.values())
        logger.info(f"Total matches: {total}")

        if output:
            logger.info(f"Results written to: {output}")

    run()



if __name__ == "__main__":
    try:
        app()
    except Exception as e:
        logger.error(f"An error occurred during execution: {e}", exc_info=True)
