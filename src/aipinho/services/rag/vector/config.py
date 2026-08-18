from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.utils.yaml_loader import load_yaml_file


def rag_config(name: str, *, critical: bool = True) -> dict[str, Any]:
    return load_yaml_file(PATHS.config_root / "rag" / name, critical=critical, root=PATHS.config_root / "rag")


def project_path(relative: str) -> Path:
    return PATHS.project_root / relative
