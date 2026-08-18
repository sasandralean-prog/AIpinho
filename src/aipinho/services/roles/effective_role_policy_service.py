from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.roles.effective_role_policy import EffectiveRolePolicy
from aipinho.schemas.roles.role_policy import RolePolicyRequest
from aipinho.services.roles.role_policy_resolver import RolePolicyResolver
from aipinho.services.roles.role_contract_service import RoleContractService
from aipinho.services.roles.role_registry_service import RoleRegistryService
from aipinho.utils.yaml_loader import load_yaml_file


class EffectiveRolePolicyService:
    def __init__(self, registry: RoleRegistryService | None = None, resolver: RolePolicyResolver | None = None, config_path: Path | None = None, contracts: RoleContractService | None = None) -> None:
        self.registry = registry or RoleRegistryService()
        self.contracts = contracts or RoleContractService(self.registry)
        self.resolver = resolver or RolePolicyResolver(self.registry, self.contracts)
        self.config_path = config_path or PATHS.config_root / "roles" / "effective_role_policy.yaml"
        self.config = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)

    def resolve(self, request: RolePolicyRequest) -> EffectiveRolePolicy:
        role_contract = self.contracts.get_contract(request.role_id)
        resolved = self.resolver.resolve(request)
        blocked = list(resolved.get("blocked_reasons", []))
        warnings = list(resolved.get("warnings", []))
        if role_contract is None:
            return EffectiveRolePolicy(role_id=request.role_id, allowed=False, blocked_reasons=list(dict.fromkeys(blocked or ["unknown_role"])), trace=list(resolved.get("trace", [])))
        policy_allowed = [str(item) for item in request.policy_decision.get("allowed_actions", [])] if isinstance(request.policy_decision, dict) else []
        policy_denied = [str(item) for item in request.policy_decision.get("denied_actions", [])] if isinstance(request.policy_decision, dict) else []
        role_allowed = [str(item) for item in role_contract.metadata.get("allowed_actions", [])]
        allowed_actions = [action for action in policy_allowed if action in role_allowed]
        denied_actions = list(dict.fromkeys([*policy_denied, *role_contract.restrictions.forbidden_actions]))
        if role_contract.permissions.can_write or role_contract.permissions.can_patch or role_contract.permissions.can_call_tools or role_contract.permissions.can_execute_tools:
            warnings.append("unsafe_role_flags_clamped")
        return EffectiveRolePolicy(
            role_id=request.role_id,
            allowed=not blocked,
            allowed_actions=allowed_actions,
            denied_actions=denied_actions,
            can_call_model=bool(role_contract.permissions.can_call_llm and not blocked),
            can_call_tools=False,
            can_write=False,
            can_patch=False,
            can_approve=False,
            model_policy=role_contract.execution_policy.model_policy,
            output_contract=role_contract.permissions.output_types_allowed[0] if role_contract.permissions.output_types_allowed else "plain_text",
            blocked_reasons=list(dict.fromkeys(blocked)),
            warnings=list(dict.fromkeys(warnings)),
            trace=[*list(resolved.get("trace", [])), {"stage": "effective_role_policy", "status": "allowed" if not blocked else "blocked", "reason": "role_cannot_expand_permissions", "source": "role_contract"}],
        )

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "effective_role_policy", "role_cannot_expand_permissions": True, "tools_enabled": False, "write_enabled": False, "patch_enabled": False}
