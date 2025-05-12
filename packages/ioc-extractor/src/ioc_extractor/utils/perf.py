import statistics
import threading
import time
from functools import wraps
from typing import Any, Callable

import psutil
from ioc_extractor.utils.logger import log


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

    log("[*] Performance Statistics", level="info")
    log(f"    Execution time          : {duration:.2f} seconds", level="info")
    log(
        f"    CPU usage (total)       : {avg_cpu:.2f}% avg | {max_cpu:.2f}% max",
        level="info",
    )
    log(
        f"    ≈ cores used            : {avg_cores_used:.2f} | {max_cores_used:.2f} of {num_cores}",
        level="info",
    )

    if per_core_avg:
        rows = []
        row = "    "
        for i, usage in enumerate(per_core_avg):
            row += f"[C{i:02}:{usage:>6.2f}%]"
            if (i + 1) % 4 == 0:
                rows.append(row)
                row = "    "
        if row.strip():
            rows.append(row)
        log("    Per-core average usage (%):", level="info")
        for r in rows:
            log(r.rstrip(), level="debug")

    log(
        f"    RAM usage               : {avg_mem:.2f} MB avg / {max_mem:.2f} MB max",
        level="info",
    )


def monitor_wrapper(enabled: bool = False):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not enabled:
                return func(*args, **kwargs)
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
