from __future__ import annotations

import fnmatch
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.analysis.project_tree_summary import ProjectTreeSummary
from aipinho.utils.yaml_loader import load_yaml_file


class ProjectProfileService:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or load_yaml_file(
            PATHS.config_root / "analysis" / "project_profiles.yaml",
            critical=True,
            root=PATHS.config_root / "analysis",
        )

    @property
    def profiles(self) -> dict[str, dict[str, Any]]:
        value = self.config.get("project_profiles", {})
        return value if isinstance(value, dict) else {}

    @property
    def fallback(self) -> dict[str, Any]:
        value = self.config.get("fallback", {})
        return value if isinstance(value, dict) else {}

    def detect(self, tree: ProjectTreeSummary) -> list[str]:
        paths = self._paths(tree)
        detected: list[str] = []
        for profile_id, profile in self.profiles.items():
            markers = [str(item) for item in profile.get("markers", []) or []]
            marker_patterns = [str(item) for item in profile.get("marker_patterns", []) or []]
            if any(marker in paths for marker in markers) or self._matches_any(paths, marker_patterns):
                detected.append(str(profile_id))
        return detected

    def priority_patterns(self, tree: ProjectTreeSummary) -> list[str]:
        patterns: list[str] = []
        for profile in self._detected_profiles(tree):
            patterns.extend(str(item) for item in profile.get("manifest_patterns", []) or [])
            patterns.extend(str(item) for item in profile.get("source_patterns", []) or [])
            patterns.extend(str(item) for item in profile.get("test_patterns", []) or [])
        if not patterns:
            patterns.extend(str(item) for item in self.fallback.get("manifest_patterns", []) or [])
            patterns.extend(str(item) for item in self.fallback.get("source_patterns", []) or [])
            patterns.extend(str(item) for item in self.fallback.get("test_patterns", []) or [])
        return list(dict.fromkeys(patterns))

    def test_patterns(self, tree: ProjectTreeSummary) -> list[str]:
        patterns: list[str] = []
        for profile in self._detected_profiles(tree):
            patterns.extend(str(item) for item in profile.get("test_patterns", []) or [])
        if not patterns:
            patterns.extend(str(item) for item in self.fallback.get("test_patterns", []) or [])
        return list(dict.fromkeys(patterns))

    def manifest_patterns(self, tree: ProjectTreeSummary) -> list[str]:
        patterns: list[str] = []
        for profile in self._detected_profiles(tree):
            patterns.extend(str(item) for item in profile.get("manifest_patterns", []) or [])
        if not patterns:
            patterns.extend(str(item) for item in self.fallback.get("manifest_patterns", []) or [])
        return list(dict.fromkeys(patterns))

    def matching_paths(self, tree: ProjectTreeSummary, patterns: list[str]) -> list[str]:
        paths = self._paths(tree)
        return sorted(path for path in paths if any(fnmatch.fnmatch(path, pattern) for pattern in patterns))

    def _detected_profiles(self, tree: ProjectTreeSummary) -> list[dict[str, Any]]:
        return [self.profiles[item] for item in self.detect(tree) if item in self.profiles]

    def _paths(self, tree: ProjectTreeSummary) -> set[str]:
        return {
            str(path).replace("\\", "/")
            for path in [*tree.top_level, *tree.important_paths, *tree.candidate_files]
        }

    def _matches_any(self, paths: set[str], patterns: list[str]) -> bool:
        return any(fnmatch.fnmatch(path, pattern) for path in paths for pattern in patterns)

    def status(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "project_profile",
            "profiles": sorted(self.profiles),
        }
