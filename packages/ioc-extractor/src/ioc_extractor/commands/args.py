import argparse

from ioc_extractor.rules.query_loader import DEFAULT_PATTERNS_URL


def parse_args():
    parser = argparse.ArgumentParser(description="Pattern-based JSON analyzer")
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        nargs="+",
        help="One or more input JSON files to process",
    )
    parser.add_argument(
        "-p",
        "--patterns",
        default=DEFAULT_PATTERNS_URL,
        help=(
            "Local path or URL to patterns JSON file. "
            "If omitted, the latest from the default GitHub repository will be fetched."
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Optional output file to save aggregated results (JSON format)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show performance statistics"
    )
    parser.add_argument(
        "-t",
        "--threads",
        type=int,
        default=None,
        help="Number of worker processes (default: number of CPU cores)",
    )
    parser.add_argument(
        "-c",
        "--chunk-size",
        type=int,
        default=None,
        help="Number of JSON objects per chunk (default: auto-detected)",
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Run benchmark mode to auto-tune threads and chunk size",
    )
    parser.add_argument(
        "--benchmark-sample-size",
        type=int,
        default=20000,
        help="Number of entries to use for benchmark mode (default: 20000)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run only the benchmark phase without processing the full dataset",
    )
    return parser.parse_args()
