from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.roles.role_definition import RoleDefinition, RoleRegistryConfig
from aipinho.utils.yaml_loader import load_yaml_file


class RoleRegistryService:
    def __init__(self, config_path: Path | None = None, config: dict[str, Any] | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "roles" / "default_roles.yaml"
        self.config = config or load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        self._roles: dict[str, RoleDefinition] | None = None

    def load(self) -> "RoleRegistryService":
        parsed = RoleRegistryConfig(**self.config)
        self._roles = parsed.roles
        self.validate()
        return self

    @property
    def roles(self) -> dict[str, RoleDefinition]:
        if self._roles is None:
            self.load()
        return self._roles or {}

    def validate(self) -> list[str]:
        warnings: list[str] = []
        seen: set[str] = set()
        for role_id, role in self.roles.items():
            if role_id in seen:
                warnings.append(f"duplicate_role:{role_id}")
            seen.add(role_id)
            if role.can_call_tools or role.can_execute_tools:
                warnings.append(f"role_tools_forced_off:{role_id}")
            if role.can_write:
                warnings.append(f"role_write_forced_off:{role_id}")
            if role.can_patch:
                warnings.append(f"role_patch_forced_off:{role_id}")
            if not role.output_contract:
                warnings.append(f"missing_output_contract:{role_id}")
        return warnings

    def get_role(self, role_id: str) -> RoleDefinition | None:
        return self.roles.get(role_id)

    def require_role(self, role_id: str) -> RoleDefinition:
        role = self.get_role(role_id)
        if role is None:
            raise ValueError("unknown_role")
        return role

    def list_roles(self) -> dict[str, RoleDefinition]:
        return dict(self.roles)

    def sanitized_roles(self) -> dict[str, dict[str, object]]:
        return {
            role_id: role.model_dump(exclude={"requires_approval"}) | {
                "can_call_tools": False,
                "can_execute_tools": False,
                "can_write": False,
                "can_patch": False,
            }
            for role_id, role in self.roles.items()
        }

    def status(self) -> dict[str, object]:
        warnings = self.validate()
        return {"status": "ok" if not warnings else "degraded", "service": "role_registry", "roles": len(self.roles), "warnings": warnings}
