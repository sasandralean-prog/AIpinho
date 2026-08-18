from __future__ import annotations

from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.utils.yaml_loader import load_yaml_file


def vision_config(name: str) -> dict:
    return load_yaml_file(PATHS.config_root / "vision" / name, critical=True, root=PATHS.config_root / "vision")


def runtime_path(*parts: str) -> Path:
    return PATHS.project_root / "data" / "runtime" / "vision" / Path(*parts)
