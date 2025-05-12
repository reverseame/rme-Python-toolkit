import statistics
import threading
import time
from functools import wraps
from typing import Any, Callable

import psutil
from ioc_extractor.utils.logger import get_logger

logger = get_logger(__name__)

def monitor_performance(
    stats: dict[str, Any], stop_event: threading.Event, interval: float = 0.5
) -> None:
    proc = psutil.Process()
    num_cores = psutil.cpu_count(logical=True)
    while not stop_event.is_set():
        # Normalize total CPU usage to a 0-100% range
        total_cpu = proc.cpu_percent(interval=None) / num_cores
        stats.setdefault("cpu", []).append(total_cpu)
        stats.setdefault("per_core", []).append(
            psutil.cpu_percent(interval=None, percpu=True)
        )
        stats.setdefault("mem", []).append(proc.memory_info().rss / 1024**2)
        time.sleep(interval)


def print_performance_stats(stats: dict[str, Any], duration: float) -> None:
    INDENT = "    "

    avg_cpu = statistics.mean(stats.get("cpu", [])) if stats.get("cpu") else 0
    max_cpu = max(stats.get("cpu", [])) if stats.get("cpu") else 0

    per_core_stats = stats.get("per_core", [])
    if per_core_stats:
        per_core_avg = [
            statistics.mean([core[i] for core in per_core_stats])
            for i in range(len(per_core_stats[0]))
        ]
    else:
        per_core_avg = []

    num_cores = psutil.cpu_count(logical=True)
    avg_cores_used = (avg_cpu / 100) * num_cores
    max_cores_used = (max_cpu / 100) * num_cores

    avg_mem = statistics.mean(stats.get("mem", [])) if stats.get("mem") else 0
    max_mem = max(stats.get("mem", [])) if stats.get("mem") else 0

    lines = [
        "[bold white]Performance Statistics[/bold white]",
        f"{INDENT}[cyan]Execution time[/cyan]          : [dim]{duration:.2f} seconds[/dim]",
        f"{INDENT}[cyan]CPU usage (total)[/cyan]       : [dim]{avg_cpu:.2f}% avg[/dim] | [dim]{max_cpu:.2f}% max[/dim]",
        f"{INDENT}[cyan]≈ cores used[/cyan]            : [dim]{avg_cores_used:.2f}[/dim] | [dim]{max_cores_used:.2f} of {num_cores}[/dim]",
    ]

    if per_core_avg:
        lines.append(f"{INDENT}[cyan]Per-core average usage (%):[/cyan]")
        row = INDENT
        for i, usage in enumerate(per_core_avg):
            row += f"[dim]C{i:02}:{usage:>5.1f}%[/dim]  "
            if (i + 1) % 4 == 0:
                lines.append(row.rstrip())
                row = INDENT
        if row.strip() != INDENT:
            lines.append(row.rstrip())

    lines.append(f"{INDENT}[cyan]RAM usage[/cyan]               : [dim]{avg_mem:.2f} MB avg[/dim] / [dim]{max_mem:.2f} MB max[/dim]")

    logger.info("\n".join(lines))


def monitor_wrapper(enabled: bool = False):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not enabled:
                return func(*args, **kwargs)

            logger.debug("Performance monitoring enabled for function.")
            stats: dict[str, Any] = {}
            stop_event = threading.Event()
            thread = threading.Thread(
                target=monitor_performance, args=(stats, stop_event), daemon=True
            )
            start = time.time()
            thread.start()
            try:
                return func(*args, **kwargs)
            finally:
                stop_event.set()
                thread.join()
                print_performance_stats(stats, time.time() - start)

        return wrapper

    return decorator
