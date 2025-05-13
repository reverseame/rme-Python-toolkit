import os
from pathlib import Path
from typing import Annotated, Optional

import typer

from ioc_extractor.rules.rule_loader import load_query_rules
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
    input: Annotated[list[Path], typer.Option("-i", "--input", help="Input JSON file(s)")],
    patterns: Annotated[list[Path], typer.Option("-p", "--patterns", help="YAML rule file(s) or directory")],
    output: Annotated[Optional[Path], typer.Option("-o", "--output", help="Output file for results")] = None,
    threads: Annotated[int, typer.Option("-t", "--threads")] = os.cpu_count(),
    chunk_size: Annotated[int, typer.Option(help="Chunk size per file")]=None,
    benchmark: Annotated[bool, typer.Option(help="Benchmark to auto-tune params")]=False,
    benchmark_sample_size: Annotated[int, typer.Option(help="Sample size for benchmark")]=20000,
    dry_run: Annotated[bool, typer.Option(help="Run only benchmark, skip full process")]=False,
    monitoring: Annotated[bool, typer.Option(help="Enable performance monitoring")]=False,
    verbose: Annotated[int, typer.Option("--verbose", "-v", count=True, callback=verbose_callback)] = 0,
):
    rules = load_query_rules(patterns)
    chunk_sizes = {}

    if benchmark:
        logger.info("Benchmark mode enabled")
        best_threads, best_chunks = benchmark_pipeline(
            input, rules,
            thread_opts=[max(1, os.cpu_count() // 2), os.cpu_count(), os.cpu_count() * 2],
            chunk_opts=[500, 1000, 2000, 4000],
            sample_count=benchmark_sample_size,
        )
        threads = best_threads
        chunk_sizes = best_chunks
        logger.info(f"Best config: threads={threads}, chunk_sizes={chunk_sizes}")

        if dry_run:
            logger.info("Dry run: exiting after benchmark.")
            raise typer.Exit()
    else:
        for infile in input:
            cs = chunk_size if chunk_size else compute_chunk_size(infile, rules)
            chunk_sizes[infile] = cs

    workers = detect_workers(threads)
    logger.info(f"Using {workers} worker(s)")

    @monitor_wrapper(enabled=monitoring)
    def run():
        counts, _ = run_pipeline(input, chunk_sizes, workers, rules, output)
        logger.info(f"Total matches: {sum(counts.values())}")

    run()

if __name__ == "__main__":
    app()
