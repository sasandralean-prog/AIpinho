from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aipinho.core.exceptions import ConfigEmptyError, ConfigNotFoundError, ConfigValidationError
from aipinho.core.paths import PATHS
from aipinho.utils.safe_paths import resolve_within_root


def load_json_file(path: Path, *, critical: bool = True, root: Path | None = None) -> dict[str, Any]:
    allowed_root = root or PATHS.project_root
    safe_path = resolve_within_root(path, allowed_root)
    if not safe_path.exists():
        if critical:
            raise ConfigNotFoundError(f"Critical config not found: {safe_path}")
        return {}
    if safe_path.stat().st_size == 0:
        if critical:
            raise ConfigEmptyError(f"Critical config is empty: {safe_path}")
        return {}
    try:
        loaded = json.loads(safe_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigValidationError(f"Invalid JSON in {safe_path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise ConfigValidationError(f"Config must be a JSON object: {safe_path}")
    return loaded
