import os
from pathlib import Path
from typing import Annotated, Optional

import typer
from common.callbacks import verbose_callback
from common.logger import get_logger
from ioc_extractor.rules.rule_loader import load_query_rules
from ioc_extractor.utils.autotune import auto_tune_resources
from ioc_extractor.utils.pipeline_executor import compute_chunk_size, run_pipeline
from ioc_extractor.utils.resource_monitor import with_resource_monitoring

logger = get_logger(__name__)
app = typer.Typer()


def resolve_chunk_config(
    input_files: list[Path],
    rules: list[dict],
    max_threads: Optional[int],
    max_chunk_size: Optional[int],
    max_ram_mb: int,
) -> tuple[int, dict[str, int]]:
    """Resolve thread and chunk configuration using auto-tuning or static values."""
    if max_threads is None or max_chunk_size is None:
        logger.info("Auto-tuning threads and chunk sizes")
        return auto_tune_resources(
            [str(p) for p in input_files],
            rules,
            thread_candidates=[
                max(1, os.cpu_count() // 2),
                os.cpu_count(),
                os.cpu_count() * 2,
            ],
            chunk_candidates=[500, 1000, 2000, 4000],
            sample_size=20000,
        )
    chunk_sizes = {
        str(infile): max_chunk_size
        or compute_chunk_size(str(infile), rules, target_ram_mb=max_ram_mb)
        for infile in input_files
    }
    return max_threads, chunk_sizes


@with_resource_monitoring(enabled=False)  # dynamically enabled at runtime
def execute_pipeline(
    input_files: list[Path],
    output: Optional[Path],
    chunk_sizes: dict[str, int],
    threads: int,
    rules: list[dict],
) -> None:
    """Run the detection pipeline and report total matches."""
    counts, _ = run_pipeline(
        inputs=[str(f) for f in input_files],
        chunk_sizes=chunk_sizes,
        workers=threads,
        rules=rules,
        output_path=str(output) if output else None,
    )
    logger.info(f"Total matches: {sum(counts.values())}")


@app.command()
def analyze(
    input: Annotated[
        list[Path], typer.Option("-i", "--input", help="Input JSON file(s)")
    ],
    patterns: Annotated[
        list[Path],
        typer.Option("-p", "--patterns", help="YAML rule file(s) or directory"),
    ],
    output: Annotated[
        Path, typer.Option("-o", "--output", help="Output file for results")
    ] = None,
    max_threads: Annotated[
        int, typer.Option("-t", "--threads", help="Maximum number of worker threads")
    ] = None,
    max_chunk_size: Annotated[
        int, typer.Option("-c", "--chunk", help="Maximum number of entries per chunk")
    ] = None,
    max_ram_mb: Annotated[
        int, typer.Option("-m", "--memory", help="Soft memory usage limit in MB")
    ] = 2048,
    diagnostics: Annotated[
        bool,
        typer.Option("-d", "--diagnostics", help="Enable resource usage reporting"),
    ] = False,
    verbose: Annotated[
        int, typer.Option("-v", "--verbose", count=True, callback=verbose_callback)
    ] = 0,
):
    """Entry point for IOC extraction using rule-based matching."""
    rules = load_query_rules(patterns)
    threads, chunk_sizes = resolve_chunk_config(
        input, rules, max_threads, max_chunk_size, max_ram_mb
    )
    logger.info(f"Running with {threads} threads")

    # Apply diagnostics at runtime to the pipeline execution
    wrapped = with_resource_monitoring(enabled=diagnostics)(execute_pipeline)
    wrapped(input, output, chunk_sizes, threads, rules)
