import os

from ioc_extractor.commands.args import parse_args
from ioc_extractor.rules.query_loader import load_query_rules
from ioc_extractor.utils.benchmark import benchmark_pipeline
from ioc_extractor.utils.logger import log
from ioc_extractor.utils.parallel import (
    compute_chunk_size,
    detect_workers,
    run_pipeline,
)
from ioc_extractor.utils.perf import monitor_wrapper


def main():
    args = parse_args()

    # Load detection rules
    rules = load_query_rules(args.patterns)

    chunk_sizes: dict[str, int] = {}

    # Benchmark mode override
    if getattr(args, "benchmark", False):
        log("[*] Benchmark mode enabled", level="info")
        thread_opts = [max(1, os.cpu_count() // 2), os.cpu_count(), os.cpu_count() * 2]
        chunk_opts = [500, 1000, 2000, 4000]
        sample_size = getattr(args, "benchmark_sample_size", 20000)

        best_threads, best_chunks = benchmark_pipeline(
            args.input, rules, thread_opts, chunk_opts, sample_count=sample_size
        )
        args.threads = best_threads
        chunk_sizes = best_chunks

        if getattr(args, "dry_run", False):
            log("[*] Dry run complete. Exiting after benchmark.", level="info")
            return

    else:
        for infile in args.input:
            if args.chunk_size:
                cs = args.chunk_size
            else:
                if args.verbose:
                    log(f"[+] Estimating chunk size for '{infile}'", level="info")
                cs = compute_chunk_size(infile, rules)
            chunk_sizes[infile] = cs
            if args.verbose:
                log(f"[+] Chunk size for '{infile}': {cs}", level="info")

    # Determine number of worker processes
    workers = detect_workers(args.threads)
    if args.verbose:
        log(f"[+] Workers: {workers}", level="info")

    # Run the processing pipeline
    @monitor_wrapper(enabled=args.verbose)
    def run():
        counts, _ = run_pipeline(
            inputs=args.input,
            chunk_sizes=chunk_sizes,
            workers=workers,
            rules=rules,
            output_path=args.output,
            verbose=args.verbose,
        )

        total = sum(counts.values())
        log(f"[*] Total matches: {total}", level="info")

        if args.output:
            log(f"[*] Results written to: {args.output}", level="info")

    run()


if __name__ == "__main__":
    main()
