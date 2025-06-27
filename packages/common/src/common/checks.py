import os
import platform
import re
import subprocess
import sys

import psutil

from common.logger import get_logger

logger = get_logger(__name__)


def is_admin() -> bool:
    """
    Returns True if the current user has administrator/root privileges.
    Works on both Windows and Unix-based systems.
    """
    if os.name == "nt":
        # Windows: use ctypes to check admin privileges
        try:
            import ctypes

            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    else:
        # Unix/Linux/macOS: check effective user ID
        return os.geteuid() == 0


def check_python() -> int:
    """
    Logs information about the Python environment.
    """
    arch = platform.architecture()[0].replace("bit", "")
    python_version = platform.python_version()
    executable_path = sys.executable

    logger.info(f"admin_root={is_admin()}")
    logger.info(f"python_architecture={arch}-bit")
    logger.info(f"python_version={python_version}")
    logger.info(f'executable_path="{executable_path}"')

    return int(arch)


def check_process_arch(pid):
    try:
        proc = psutil.Process(pid)
        exe_path = proc.exe()

        result = subprocess.check_output(["file", exe_path]).decode()

        match = re.search(r"ELF (\d+)-bit", result)
        if not match:
            raise Exception("Could not determine architecture")

        arch = match.group(1)
        logger.info(f"python_architecture={arch}-bit")
        return int(arch)

    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        logger.error(f"Error accessing process: {e}")
        raise
