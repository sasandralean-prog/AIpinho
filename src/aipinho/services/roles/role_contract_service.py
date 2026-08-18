from __future__ import annotations

from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.roles.role_contracts import (
    RoleCapability,
    RoleContract,
    RoleExecutionPolicy,
    RoleLifecycle,
    RolePermission,
    RoleRestriction,
)
from aipinho.services.policy_kernel.action_registry_service import ActionRegistryService
from aipinho.services.roles.role_registry_service import RoleRegistryService


class RoleContractService:
    def __init__(self, registry: RoleRegistryService | None = None, action_registry: ActionRegistryService | None = None) -> None:
        self.registry = registry or RoleRegistryService()
        self.action_registry = action_registry or ActionRegistryService().load()

    def get_contract(self, role_id: str) -> RoleContract | None:
        role = self.registry.get_role(role_id)
        if role is None:
            return None
        return self._from_role(role_id, role)

    def list_contracts(self) -> dict[str, RoleContract]:
        return {role_id: self._from_role(role_id, role) for role_id, role in self.registry.list_roles().items()}

    def _from_role(self, role_id: str, role) -> RoleContract:
        allowed_actions = self._normalize_actions(role.allowed_actions)
        forbidden_actions = self._normalize_actions(role.forbidden_actions)
        requires_approval = self._normalize_actions(role.requires_approval)
        capabilities = [
            RoleCapability(capability_id=str(item), description="purpose")
            for item in [*role.allowed_purposes, *role.allowed_task_types]
        ]
        permissions = RolePermission(
            can_call_llm=bool(role.can_call_model),
            can_call_tools=False,
            can_execute_tools=False,
            can_write=False,
            can_patch=False,
            can_approve=bool(role.can_approve),
            tools_allowed=[],
            skills_allowed=[],
            output_types_allowed=[role.output_contract],
            requires_approval=requires_approval,
        )
        restrictions = RoleRestriction(
            forbidden_actions=forbidden_actions,
            tools_forced_off=True,
            writes_forced_off=True,
            patches_forced_off=True,
            runtime_execution_forbidden=True,
        )
        lifecycle = RoleLifecycle(status="enabled" if role.enabled else "disabled", source_config=str(Path(PATHS.config_root / "roles" / "default_roles.yaml")))
        execution_policy = RoleExecutionPolicy(
            model_policy=role.default_model_policy,
            side_effects_allowed=False,
            approval_required_for_side_effects=True,
            allowed_purposes=list(role.allowed_purposes),
        )
        return RoleContract(
            role_id=role_id,
            description=role.description,
            purpose=role.purpose,
            capabilities=capabilities,
            permissions=permissions,
            restrictions=restrictions,
            lifecycle=lifecycle,
            execution_policy=execution_policy,
            metadata={"source": "default_roles_yaml", "allowed_actions": allowed_actions},
        )

    def _normalize_actions(self, actions: list[str]) -> list[str]:
        normalized: list[str] = []
        for action in actions:
            normalized.append(self.action_registry.normalize_action(action))
        return list(dict.fromkeys(normalized))

    def status(self) -> dict[str, object]:
        contracts = self.list_contracts()
        return {"status": "ok" if contracts else "degraded", "service": "role_contracts", "roles": len(contracts)}
