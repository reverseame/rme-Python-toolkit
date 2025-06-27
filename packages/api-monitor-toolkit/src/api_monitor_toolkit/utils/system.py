from pathlib import Path

import pefile


def detect_architecture(binary_path: Path) -> str:
    pe = pefile.PE(str(binary_path))
    return "x64" if pe.FILE_HEADER.Machine == 0x8664 else "x86"
