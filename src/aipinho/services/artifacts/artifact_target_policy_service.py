from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.utils.yaml_loader import inspect_yaml_file, load_yaml_file


class ArtifactTargetPolicyService:
    def __init__(self, path: Path | None = None, policy: dict[str, Any] | None = None) -> None:
        self.path = path or PATHS.config_root / "artifacts" / "artifact_target_policy.yaml"
        self.policy = policy or load_yaml_file(self.path, critical=True, root=PATHS.config_root / "artifacts")

    @property
    def targets(self) -> dict[str, object]:
        return self.policy.get("targets", {}) if isinstance(self.policy.get("targets"), dict) else {}

    @property
    def path_rules(self) -> dict[str, object]:
        return self.policy.get("path_rules", {}) if isinstance(self.policy.get("path_rules"), dict) else {}

    @property
    def overwrite(self) -> dict[str, object]:
        return self.policy.get("overwrite", {}) if isinstance(self.policy.get("overwrite"), dict) else {}

    def allowed_extensions(self) -> list[str]:
        return [str(item).lower() for item in self.targets.get("allowed_extensions", []) or []]

    def blocked_extensions(self) -> list[str]:
        return [str(item).lower() for item in self.targets.get("blocked_extensions", []) or []]

    def allowed_base_dirs(self) -> list[str]:
        return [str(item).replace("\\", "/").strip("/").lower() for item in self.targets.get("allowed_base_dirs", []) or []]

    def allowed_workspace_roots(self) -> list[str]:
        roots = [str(item) for item in self.targets.get("allowed_workspace_roots", []) or []]
        if os.environ.get("AIPINHO_TEST_PROFILE") == "1":
            test_root = os.environ.get("AIPINHO_TEST_MUTABLE_ROOT", "").strip()
            if test_root:
                roots.append(test_root)
        return list(dict.fromkeys(roots))

    def blocked_base_dirs(self) -> list[str]:
        return [str(item).replace("\\", "/").strip("/").lower() for item in self.targets.get("blocked_base_dirs", []) or []]

    def forbidden_roots(self) -> list[str]:
        return [str(item) for item in self.policy.get("forbidden_roots", []) or []]

    def status(self) -> dict[str, object]:
        status = inspect_yaml_file(self.path, root=PATHS.config_root / "artifacts")
        return {
            "status": status.status,
            "service": "artifact_target_policy",
            "allowed_extensions": self.allowed_extensions(),
            "blocked_extensions": self.blocked_extensions(),
            "allowed_workspace_roots": self.allowed_workspace_roots(),
            "allowed_base_dirs": self.allowed_base_dirs(),
            "source_code_targets_blocked": True,
        }
