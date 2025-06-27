import statistics
import threading
import time
from functools import wraps
from typing import Any, Callable

import humanfriendly
import psutil
from common.logger import get_logger

logger = get_logger(__name__)


def _monitor(
    stats: dict[str, Any], stop: threading.Event, interval: float = 0.5
) -> None:
    """Collect CPU and memory usage statistics in background."""
    proc = psutil.Process()
    num_cores = psutil.cpu_count(logical=True)
    while not stop.is_set():
        total_cpu = proc.cpu_percent(interval=None) / num_cores
        stats.setdefault("cpu", []).append(total_cpu)
        stats.setdefault("per_core", []).append(
            psutil.cpu_percent(interval=None, percpu=True)
        )
        stats.setdefault("mem", []).append(proc.memory_info().rss / 1024**2)
        time.sleep(interval)


def _summarize(stats: dict[str, Any], duration: float) -> None:
    """Log formatted performance metrics after execution."""
    avg_cpu = statistics.mean(stats.get("cpu", [])) if stats.get("cpu") else 0
    max_cpu = max(stats.get("cpu", [])) if stats.get("cpu") else 0
    per_core_stats = stats.get("per_core", [])
    per_core_avg = (
        [
            statistics.mean([core[i] for core in per_core_stats])
            for i in range(len(per_core_stats[0]))
        ]
        if per_core_stats
        else []
    )
    avg_mem = statistics.mean(stats.get("mem", [])) if stats.get("mem") else 0
    max_mem = max(stats.get("mem", [])) if stats.get("mem") else 0
    num_cores = psutil.cpu_count(logical=True)
    total_ram = psutil.virtual_memory().total / (1024**2)
    avg_cores_used = (avg_cpu / 100) * num_cores
    max_cores_used = (max_cpu / 100) * num_cores

    lines = [
        "Resource usage summary",
        f"Duration           : {humanfriendly.format_timespan(duration)}",
        f"CPU usage          : {avg_cpu:.2f}% avg / {max_cpu:.2f}% max",
        f"Logical cores used : {avg_cores_used:.2f} / {max_cores_used:.2f} of {num_cores}",
        f"RAM usage          : {avg_mem:.2f} MB avg / {max_mem:.2f} MB max of {total_ram:.0f} MB",
    ]

    if per_core_avg:
        lines.append("")
        lines.append("Per-core average usage (%):")
        row = ""
        for i, usage in enumerate(per_core_avg):
            row += f"C{i:02}:{usage:>5.1f}%  "
            if (i + 1) % 4 == 0:
                lines.append(row.rstrip())
                row = ""
        if row.strip():
            lines.append(row.rstrip())

    logger.info("\n".join(lines))


def with_resource_monitoring(enabled: bool = False):
    """Decorator to report CPU and RAM usage if diagnostics are enabled."""

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not enabled:
                return func(*args, **kwargs)

            logger.debug("Diagnostics enabled: monitoring system resources.")
            stats: dict[str, Any] = {}
            stop_event = threading.Event()
            thread = threading.Thread(
                target=_monitor, args=(stats, stop_event), daemon=True
            )
            start = time.time()
            thread.start()
            try:
                return func(*args, **kwargs)
            finally:
                stop_event.set()
                thread.join()
                _summarize(stats, time.time() - start)

        return wrapper

    return decorator
