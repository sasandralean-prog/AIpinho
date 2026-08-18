from __future__ import annotations

import os
from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.utils.yaml_loader import load_yaml_file


def sandbox_root() -> Path:
    override = os.environ.get("AIPINHO_SANDBOX_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    config = load_yaml_file(PATHS.config_root / "sandbox" / "sandbox_policy.yaml", critical=False, root=PATHS.config_root)
    configured = config.get("sandbox_root") or config.get("root_policy", {}).get("default_root")
    return Path(str(configured)).expanduser().resolve() if configured else (PATHS.project_root / "sandboxes").resolve()


def sandbox_data_root() -> Path:
    override = os.environ.get("AIPINHO_SANDBOX_DATA_ROOT")
    return Path(override).expanduser().resolve() if override else (PATHS.project_root / "data" / "runtime" / "sandbox").resolve()


def ensure_sandbox_dirs() -> dict[str, Path]:
    root = sandbox_root()
    dirs = {
        "root": root,
        "default": root / "default",
        "tasks": root / "tasks",
        "projects": root / "projects",
        "artifacts": root / "artifacts",
        "tmp": root / "tmp",
        "trash": root / "trash",
        "reports": root / "reports",
        "logs": root / "logs",
        "data": sandbox_data_root(),
    }
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def is_relative_path_safe(value: str) -> bool:
    path = Path(value)
    if path.is_absolute():
        return False
    parts = set(path.parts)
    return ".." not in parts and "" not in parts


def is_within(child: Path, parent: Path) -> bool:
    try:
        child_resolved = child.resolve(strict=False)
        parent_resolved = parent.resolve(strict=False)
        return child_resolved == parent_resolved or parent_resolved in child_resolved.parents
    except OSError:
        child_text = str(child.absolute()).casefold()
        parent_text = str(parent.absolute()).casefold().rstrip("\\/")
        return child_text == parent_text or child_text.startswith(parent_text + os.sep)
