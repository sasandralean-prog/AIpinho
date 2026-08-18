from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    project_root: Path
    src_root: Path
    package_root: Path
    config_root: Path
    reports_root: Path


def discover_project_paths() -> ProjectPaths:
    package_root = Path(__file__).resolve().parents[1]
    src_root = package_root.parent
    project_root = src_root.parent
    return ProjectPaths(
        project_root=project_root,
        src_root=src_root,
        package_root=package_root,
        config_root=project_root / "config",
        reports_root=project_root / "reports",
    )


PATHS = discover_project_paths()
