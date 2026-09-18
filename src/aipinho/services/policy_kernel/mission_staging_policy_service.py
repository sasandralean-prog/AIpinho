from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.runtime.mission_contract import MissionContract, MissionResourceScope
from aipinho.utils.yaml_loader import load_yaml_file


class MissionStagingPolicyService:
    """Static upper bounds for mission-derived staging resources."""

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "policies" / "mission_staging_policy.yaml"
        self._config: dict[str, Any] | None = None

    @property
    def config(self) -> dict[str, Any]:
        if self._config is None:
            payload = load_yaml_file(
                self.config_path,
                critical=True,
                root=self.config_path.parent,
            )
            self._config = dict(payload.get("mission_staging") or {})
        return self._config
    def safe_root(self) -> Path:
        cfg = self.config
        if not bool(cfg.get("enabled", False)):
            raise ValueError("mission_staging_disabled")
        strategy = str(cfg.get("root_strategy") or "system_temp")
        directory_name = str(cfg.get("directory_name") or "aipinho_mission_staging").strip()
        if not directory_name or any(part in directory_name for part in ("/", "\\", "..")):
            raise ValueError("mission_staging_directory_name_invalid")
        if strategy == "system_temp":
            root = Path(tempfile.gettempdir()) / directory_name
        elif strategy == "configured_absolute":
            configured = str(cfg.get("configured_root") or "").strip()
            if not configured or not Path(configured).expanduser().is_absolute():
                raise ValueError("mission_staging_configured_root_invalid")
            root = Path(configured).expanduser()
        else:
            raise ValueError("mission_staging_root_strategy_invalid")
        return root.resolve(strict=False)

    def allowed_permissions(self) -> list[str]:
        values = [str(item) for item in self.config.get("allowed_permissions", []) or []]
        return list(dict.fromkeys(item for item in values if item))
    def validate_derived_resource(
        self,
        *,
        parent: MissionContract,
        resource: MissionResourceScope,
    ) -> None:
        if resource.resource_type != "mission_staging":
            raise ValueError("mission_staging_resource_type_invalid")
        if resource.role != "temp_staging":
            raise ValueError("mission_staging_role_invalid")
        if not resource.locator:
            raise ValueError("mission_staging_locator_missing")
        if not self._is_under(resource.locator, str(self.safe_root())):
            raise ValueError("mission_staging_outside_safe_root")
        remote = next(
            (item for item in parent.remote_resources if item.resource_id == resource.derived_from),
            None,
        )
        if remote is None or remote.resource_type != "remote_repository":
            raise ValueError("mission_staging_source_remote_missing")
        if not set(resource.permissions).issubset(set(self.allowed_permissions())):
            raise ValueError("mission_staging_permission_outside_policy")
        metadata = dict(resource.metadata or {})
        if str(metadata.get("lifetime") or "") != str(self.config.get("lifetime") or "mission"):
            raise ValueError("mission_staging_lifetime_invalid")
        if str(metadata.get("source_remote_resource_id") or "") != remote.resource_id:
            raise ValueError("mission_staging_source_remote_mismatch")
        if str(metadata.get("source_remote_identity") or "") != str(remote.normalized_identity or ""):
            raise ValueError("mission_staging_source_identity_mismatch")
        if list(metadata.get("source_allowed_branches") or []) != list(remote.allowed_branches):
            raise ValueError("mission_staging_source_branches_mismatch")
        if list(metadata.get("authority_inherited") or []):
            raise ValueError("mission_staging_human_authority_must_not_inherit")
        not_inherited = {str(item) for item in metadata.get("authority_not_inherited", []) or []}
        relevant_authority = set(parent.authority.authorized_capabilities).intersection(remote.permissions)
        if not relevant_authority.issubset(not_inherited):
            raise ValueError("mission_staging_authority_noninheritance_incomplete")
        evidence = {str(item) for item in metadata.get("creation_evidence", []) or []}
        required = {
            f"mission:{parent.mission_id}",
            f"remote_resource:{remote.resource_id}",
            "mission_staging_policy:v1",
        }
        if not required.issubset(evidence):
            raise ValueError("mission_staging_creation_evidence_incomplete")

    @staticmethod
    def _normalize(value: str) -> str:
        return os.path.normcase(str(Path(value).expanduser().resolve(strict=False)))

    def _is_under(self, path: str, root: str) -> bool:
        normalized_path = self._normalize(path)
        normalized_root = self._normalize(root)
        return normalized_path == normalized_root or normalized_path.startswith(normalized_root + os.sep)
