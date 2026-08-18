from __future__ import annotations

from pathlib import Path
import re


def safe_filename(name: str) -> str:
    basename = Path(name).name
    return re.sub(r"[^A-Za-z0-9._-]", "_", basename) or "artifact.bin"
