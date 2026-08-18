from __future__ import annotations

from aipinho.schemas.roles.role_policy import RolePolicyRequest
from aipinho.services.roles.role_contract_service import RoleContractService
from aipinho.services.roles.role_registry_service import RoleRegistryService


class RolePolicyResolver:
    def __init__(self, registry: RoleRegistryService | None = None, contracts: RoleContractService | None = None) -> None:
        self.registry = registry or RoleRegistryService()
        self.contracts = contracts or RoleContractService(self.registry)

    def resolve(self, request: RolePolicyRequest) -> dict[str, object]:
        role_contract = self.contracts.get_contract(request.role_id)
        blocked: list[str] = []
        warnings: list[str] = []
        if role_contract is None:
            blocked.append("unknown_role")
        elif role_contract.lifecycle.status != "enabled":
            blocked.append("role_disabled")
        policy_status = str(request.policy_decision.get("status", "allowed")) if isinstance(request.policy_decision, dict) else "allowed"
        if policy_status in {"denied", "blocked"}:
            blocked.append("policy_denied")
        requested_actions = [str(item) for item in request.task_contract.get("requested_actions", [])] if isinstance(request.task_contract, dict) else []
        denied_actions = [str(item) for item in request.policy_decision.get("denied_actions", [])] if isinstance(request.policy_decision, dict) else []
        if any(action in denied_actions for action in requested_actions):
            blocked.append("requested_action_denied")
        if role_contract and (
            role_contract.permissions.can_call_tools
            or role_contract.permissions.can_execute_tools
            or role_contract.permissions.can_write
            or role_contract.permissions.can_patch
        ):
            warnings.append("role_permissions_forced_to_safe_envelope")
        return {
            "allowed": not blocked,
            "role_id": request.role_id,
            "blocked_reasons": list(dict.fromkeys(blocked)),
            "warnings": list(dict.fromkeys(warnings)),
            "trace": [{"stage": "role_policy_resolver", "status": "allowed" if not blocked else "blocked", "reason": ",".join(blocked), "source": "role_contract"}],
        }

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "role_policy_resolver"}
