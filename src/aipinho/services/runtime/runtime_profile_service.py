from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.utils.yaml_loader import load_yaml_file


class RuntimeProfileService:
    """Loads operation profiles without embedding product cases in runtime code."""

    CONTRACT_DEFAULTS = {
        "conversation": "conversation",
        "delegation_request": "delegation_parent",
        "analysis_readonly": "readonly_analysis",
        "readonly_analysis": "readonly_analysis",
        "in_chat_final_report": "conversation",
        "validation": "validation",
        "validation_request": "validation",
        "artifact_generation": "artifact_generation",
        "artifact_build": "artifact_generation",
        "patch_request": "patch",
        "patch_apply": "patch",
        "filesystem_write": "write_file",
        "file_modification": "write_file",
        "shell_execution": "shell",
        "project_generation": "project_generation",
        "project_build": "project_generation",
        "web_search": "web_search",
    }

    def __init__(self, profiles_root: Path | None = None) -> None:
        self.profiles_root = profiles_root or PATHS.config_root / "runtime" / "profiles"
        self._profiles: dict[str, dict[str, Any]] = {}
        self._operations: dict[str, str] = {}

    def load(self) -> "RuntimeProfileService":
        profiles: dict[str, dict[str, Any]] = {}
        operations: dict[str, str] = {}
        for path in sorted(self.profiles_root.glob("*.yaml")):
            payload = load_yaml_file(path, critical=True, root=self.profiles_root)
            profile = payload.get("profile", {}) if isinstance(payload, dict) else {}
            if not isinstance(profile, dict):
                raise ValueError(f"invalid_runtime_profile:{path.name}")
            profile_id = str(profile.get("id") or path.stem)
            if profile_id in profiles:
                raise ValueError(f"duplicate_runtime_profile:{profile_id}")
            profiles[profile_id] = profile
            for operation in profile.get("operation_types", []) or []:
                operation_id = str(operation)
                previous = operations.get(operation_id)
                if previous and previous != profile_id:
                    raise ValueError(f"duplicate_runtime_operation:{operation_id}")
                operations[operation_id] = profile_id
        self._profiles = profiles
        self._operations = operations
        return self

    def resolve(
        self,
        *,
        operation_type: str | None,
        contract_type: str,
        requested_profile: str | None = None,
    ) -> dict[str, Any] | None:
        if not self._profiles:
            self.load()
        profile_id = requested_profile
        if not profile_id and operation_type:
            profile_id = self._operations.get(operation_type)
        if not profile_id:
            profile_id = self.CONTRACT_DEFAULTS.get(contract_type)
        profile = self._profiles.get(str(profile_id)) if profile_id else None
        return dict(profile) if profile is not None else None

    def get(self, profile_id: str) -> dict[str, Any] | None:
        if not self._profiles:
            self.load()
        profile = self._profiles.get(profile_id)
        return dict(profile) if profile is not None else None

    def status(self) -> dict[str, Any]:
        try:
            self.load()
            return {
                "status": "ok",
                "profiles": sorted(self._profiles),
                "operation_types": len(self._operations),
            }
        except Exception as exc:
            return {"status": "degraded", "error": str(exc)}
