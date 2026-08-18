from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.roles.role_model_binding import DisabledRoleModelBinding, RoleModelBinding
from aipinho.utils.yaml_loader import load_yaml_file


class RoleModelBindingService:
    def __init__(self, config_path: Path | None = None, config: dict[str, Any] | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "roles" / "role_model_bindings.yaml"
        self.config = config or load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        self._bindings: dict[str, RoleModelBinding] | None = None
        self._disabled: dict[str, DisabledRoleModelBinding] | None = None

    @property
    def bindings(self) -> dict[str, RoleModelBinding]:
        if self._bindings is None:
            raw = self.config.get("role_model_bindings", {}) if isinstance(self.config.get("role_model_bindings", {}), dict) else {}
            self._bindings = {
                str(role_id): RoleModelBinding(role_id=str(role_id), **value)
                for role_id, value in raw.items()
                if isinstance(value, dict)
            }
        return self._bindings

    @property
    def disabled_bindings(self) -> dict[str, DisabledRoleModelBinding]:
        if self._disabled is None:
            raw = self.config.get("disabled_until_future_sprints", {}) if isinstance(self.config.get("disabled_until_future_sprints", {}), dict) else {}
            self._disabled = {
                str(role_id): DisabledRoleModelBinding(role_id=str(role_id), reason=str(value.get("reason", "disabled_until_future_sprint")))
                for role_id, value in raw.items()
                if isinstance(value, dict)
            }
        return self._disabled

    def list_bindings(self) -> list[RoleModelBinding]:
        return [self.bindings[key] for key in sorted(self.bindings)]

    def get_binding(self, role_id: str) -> RoleModelBinding | None:
        return self.bindings.get(role_id)

    def resolve_binding(self, role_id: str) -> RoleModelBinding | None:
        direct = self.get_binding(role_id)
        if direct is not None:
            return direct
        aliases = self.config.get("role_aliases", {}) if isinstance(self.config.get("role_aliases", {}), dict) else {}
        target = str(aliases.get(role_id) or "")
        return self.get_binding(target) if target else None

    def get_disabled(self, role_id: str) -> DisabledRoleModelBinding | None:
        return self.disabled_bindings.get(role_id)

    def status(self) -> dict[str, object]:
        coder = self.get_binding("coder")
        return {
            "status": "ok" if coder and coder.primary_model == "qwen2_5_coder_7b_q4_k_m" else "degraded",
            "service": "role_model_binding",
            "bindings": len(self.bindings),
            "disabled_future_bindings": len(self.disabled_bindings),
            "default_coding_model": coder.primary_model if coder else None,
            "aliases": len(self.config.get("role_aliases", {}) or {}),
        }
