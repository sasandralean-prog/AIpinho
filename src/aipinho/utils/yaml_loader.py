from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from aipinho.core.exceptions import ConfigEmptyError, ConfigNotFoundError, ConfigValidationError
from aipinho.core.paths import PATHS
from aipinho.utils.safe_paths import resolve_within_root


@dataclass(frozen=True)
class ConfigFileStatus:
    path: str
    exists: bool
    empty: bool
    status: str
    warning: str | None = None


def load_yaml_file(path: Path, *, critical: bool = True, root: Path | None = None) -> dict[str, Any]:
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
        loaded = yaml.safe_load(safe_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigValidationError(f"Invalid YAML in {safe_path}: {exc}") from exc
    if loaded is None:
        if critical:
            raise ConfigEmptyError(f"Critical config has no YAML content: {safe_path}")
        return {}
    if not isinstance(loaded, dict):
        raise ConfigValidationError(f"Config must be a YAML mapping: {safe_path}")
    return loaded


def inspect_yaml_file(path: Path, *, root: Path | None = None) -> ConfigFileStatus:
    allowed_root = root or PATHS.project_root
    safe_path = resolve_within_root(path, allowed_root)
    if not safe_path.exists():
        return ConfigFileStatus(str(safe_path), exists=False, empty=True, status="missing", warning="file not found")
    is_empty = safe_path.stat().st_size == 0
    if is_empty:
        return ConfigFileStatus(str(safe_path), exists=True, empty=True, status="degraded", warning="file is empty")
    return ConfigFileStatus(str(safe_path), exists=True, empty=False, status="ok")
