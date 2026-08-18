from __future__ import annotations

from aipinho.core.paths import PATHS
from aipinho.utils.yaml_loader import load_yaml_file


def integration_config(name: str) -> dict:
    root = PATHS.config_root / "rag" / "integration"
    return load_yaml_file(root / name, critical=True, root=root)
