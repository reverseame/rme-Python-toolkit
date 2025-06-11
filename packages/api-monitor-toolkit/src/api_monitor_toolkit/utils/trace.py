import shutil
import sys
import time
import zipfile
from pathlib import Path

import requests
from api_monitor_toolkit.core.monitor import bring_monitor_to_front, send_text
from common.logger import get_logger

logger = get_logger(__name__)


def save_apmx(shell, path: Path, timeout: int):
    if not bring_monitor_to_front():
        logger.warning("API Monitor window not found when attempting to save .apmx.")
    shell.SendKeys("^s")
    time.sleep(0.2)
    send_text(shell, str(path))
    shell.SendKeys("{ENTER}")
    time.sleep(timeout)


def get_results(temp_dir: Path) -> list[Path]:
    return list(temp_dir.glob("*.apmx*"))


def save_results(results: list[Path], output: str, temp: Path, base_name: str):
    if not results:
        logger.warning("No .apmx files found to save")
    zip_path = temp / f"{base_name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in results:
            zf.write(f, arcname=f.name)

    if output.lower().startswith("http"):
        with open(zip_path, "rb") as f:
            resp = requests.post(output, files={"file": f})
            if resp.status_code != 200:
                logger.error(f"Upload failed: HTTP {resp.status_code}")
                sys.exit(1)
        logger.info(f"Results uploaded to {output}")
        zip_path.unlink(missing_ok=True)
        return

    out_path = Path(output)
    if out_path.suffix.lower() == ".zip":
        shutil.move(str(zip_path), out_path)
        logger.info(f"Results saved to {out_path.resolve()}")
        return

    logger.error(f"Invalid output path '{output}'. Must be a .zip or an HTTP URL.")
    sys.exit(1)
