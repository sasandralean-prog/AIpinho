from __future__ import annotations

from pathlib import Path

from aipinho.core.exceptions import ConfigValidationError
from aipinho.core.paths import PATHS
from aipinho.schemas.roles.role_definition import RoleDefinition, RoleRegistryConfig
from aipinho.services.policy_kernel.action_registry_service import ActionRegistryService
from aipinho.utils.yaml_loader import load_yaml_file


class RoleRegistry:
    EXPECTED_ROLES = {
        "planner",
        "supervisor",
        "executor",
        "artifact_writer",
        "reporter",
        "interpreter",
        "speaker",
        "debugger",
        "memory_curator",
        "retriever",
        "reranker",
        "validator",
    }

    def __init__(self, config_path: Path | None = None, action_registry: ActionRegistryService | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "roles" / "default_roles.yaml"
        self.action_registry = action_registry or ActionRegistryService().load()
        self._config: RoleRegistryConfig | None = None

    def load(self) -> "RoleRegistry":
        data = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        self._config = RoleRegistryConfig(**data)
        self.validate()
        return self

    @property
    def config(self) -> RoleRegistryConfig:
        if self._config is None:
            self.load()
        if self._config is None:
            raise ConfigValidationError("Role registry could not be loaded")
        return self._config

    def validate(self) -> None:
        roles = self.config.roles
        missing = sorted(self.EXPECTED_ROLES - set(roles))
        if missing:
            raise ConfigValidationError(f"Missing expected roles: {missing}")
        for role_id, role in roles.items():
            if role.can_write and not role.can_execute_tools:
                raise ConfigValidationError(f"Role cannot write without tool execution capability: {role_id}")
            for field_name in ("allowed_actions", "forbidden_actions", "requires_approval"):
                for action in getattr(role, field_name):
                    self.action_registry.normalize_action(action)
            if role_id == "artifact_writer" and "apply_patch" not in [self.action_registry.normalize_action(a) for a in role.forbidden_actions]:
                raise ConfigValidationError("artifact_writer must forbid apply_patch")
            if role_id in {"speaker", "interpreter", "debugger"} and role.can_execute_tools:
                raise ConfigValidationError(f"{role_id} cannot execute tools")

    def get_role(self, role_id: str) -> RoleDefinition:
        self.validate()
        role = self.config.roles.get(role_id)
        if role is None:
            raise ConfigValidationError(f"Unknown role: {role_id}")
        return role

    def list_roles(self) -> dict[str, RoleDefinition]:
        self.validate()
        return self.config.roles

    def status(self) -> dict[str, object]:
        try:
            self.validate()
            return {"status": "ok", "roles": len(self.config.roles)}
        except Exception as exc:
            return {"status": "degraded", "error": str(exc)}

