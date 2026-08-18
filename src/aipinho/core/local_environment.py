from __future__ import annotations

import os
from pathlib import Path

from aipinho.core.paths import PATHS


def load_local_environment(
    path: Path | None = None,
    *,
    override: bool = False,
) -> int:
    """Load a local dotenv-style file without logging names or values."""

    env_path = path or (PATHS.project_root / ".env.local")
    if not env_path.is_file():
        return 0

    loaded = 0
    for raw_line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue
        name, raw_value = line.split("=", 1)
        name = name.strip()
        if not name or not name.replace("_", "").isalnum():
            continue
        value = _parse_value(raw_value.strip())
        if override or name not in os.environ:
            os.environ[name] = value
            loaded += 1
    return loaded


def _parse_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    comment_at = value.find(" #")
    if comment_at >= 0:
        return value[:comment_at].rstrip()
    return value
