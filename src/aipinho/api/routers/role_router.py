from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.schemas.roles.role_model_gate import RoleModelGateRequest
from aipinho.schemas.roles.role_pass_input import RolePassInput
from aipinho.schemas.roles.role_policy import RolePolicyRequest
from aipinho.services.roles.effective_role_policy_service import EffectiveRolePolicyService
from aipinho.services.roles.role_model_gate_service import RoleModelGateService
from aipinho.services.roles.role_pass_runner import RolePassRunner
from aipinho.services.roles.role_registry_service import RoleRegistryService

router = APIRouter(prefix="/api/v1/roles", tags=["roles"])


@router.get("")
def list_roles() -> dict[str, object]:
    service = RoleRegistryService()
    return {"status": "ok", "roles": service.sanitized_roles(), "tools_enabled": False, "write_enabled": False, "patch_enabled": False}


@router.get("/{role_id}")
def get_role(role_id: str) -> dict[str, object]:
    role = RoleRegistryService().get_role(role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="unknown_role")
    return {"status": "ok", "role_id": role_id, "role": role.model_dump() | {"can_call_tools": False, "can_execute_tools": False, "can_write": False, "can_patch": False}}


@router.post("/{role_id}/effective-policy")
def resolve_effective_policy(role_id: str, request: RolePolicyRequest) -> dict[str, object]:
    payload = request.model_copy(update={"role_id": role_id})
    policy = EffectiveRolePolicyService().resolve(payload)
    return {"status": "ok" if policy.allowed else "blocked", "effective_policy": policy}


@router.post("/{role_id}/model-gate")
def resolve_model_gate(role_id: str, request: RoleModelGateRequest) -> dict[str, object]:
    payload = request.model_copy(update={"role_id": role_id})
    decision = RoleModelGateService().decide(payload)
    return {"status": decision.status, "model_gate": decision}


@router.post("/{role_id}/run-pass")
def run_role_pass(role_id: str, request: RolePassInput) -> dict[str, object]:
    payload = request.model_copy(update={"role_id": role_id})
    result = RolePassRunner().run(payload)
    return {"status": result.status, "pass": result, "tools_enabled": False, "write_enabled": False, "patch_enabled": False}
