from __future__ import annotations

from fastapi import APIRouter

from aipinho.schemas.policy.policy_decision import PolicyResolveRequest
from aipinho.services.governance.policy.effective_policy_decision_service import (
    EffectivePolicyDecisionService,
)
from aipinho.services.policy_kernel.action_registry_service import ActionRegistryService
from aipinho.services.policy_kernel.approval_policy_service import ApprovalPolicyService
from aipinho.services.policy_kernel.capability_gate_service import CapabilityRegistryService
from aipinho.services.policy_kernel.policy_precedence_service import PolicyPrecedenceService
from aipinho.services.policy_kernel.workspace_policy_service import WorkspacePolicyService

router = APIRouter(prefix="/api/v1/policy", tags=["policy"])


def _safe_status(factory):
    try:
        return factory()
    except Exception as exc:
        return {"status": "degraded", "error": str(exc)}


@router.get("/status")
def get_policy_status() -> dict[str, object]:
    action_registry = ActionRegistryService().load()
    action_status = _safe_status(lambda: action_registry.status())
    precedence_status = _safe_status(lambda: PolicyPrecedenceService().load().status())
    capability_status = _safe_status(lambda: CapabilityRegistryService().load().status())
    approval_status = _safe_status(lambda: ApprovalPolicyService(action_registry=action_registry).load().status())
    workspace_status = _safe_status(lambda: WorkspacePolicyService().load().status())
    effective_status = _safe_status(lambda: EffectivePolicyDecisionService().status())
    statuses = (action_status, precedence_status, capability_status, approval_status, workspace_status, effective_status)
    return {
        "status": "ok" if all(item.get("status") == "ok" for item in statuses) else "degraded",
        "action_registry": action_status,
        "policy_precedence": precedence_status,
        "capability_registry": capability_status,
        "approval_policy": approval_status,
        "workspace_policy": workspace_status,
        "effective_policy_decision": effective_status,
    }


@router.get("/actions")
def get_policy_actions() -> dict[str, object]:
    registry = ActionRegistryService().load()
    return {
        "status": "ok",
        "actions": {name: action.dict() for name, action in registry.list_actions().items()},
        "aliases": registry.aliases(),
    }


@router.get("/precedence")
def get_policy_precedence() -> dict[str, object]:
    return {"status": "ok", **PolicyPrecedenceService().load().explain()}


@router.get("/capabilities")
def get_policy_capabilities() -> dict[str, object]:
    registry = CapabilityRegistryService().load()
    return {
        "status": "ok",
        "capabilities": {name: capability.dict() for name, capability in registry.list_capabilities().items()},
    }


@router.get("/approvals")
def get_policy_approvals() -> dict[str, object]:
    service = ApprovalPolicyService().load()
    return {"status": "ok", **service.status()}


@router.post("/resolve")
def resolve_policy(request: PolicyResolveRequest):
    decision, canonical = EffectivePolicyDecisionService().resolve_policy_request(request)
    data = decision.model_dump()
    data["canonical_policy"] = canonical.model_dump(mode="json")
    data["canonical_source"] = "effective_policy_decision"
    return data


@router.post("/explain")
def explain_policy(request: PolicyResolveRequest) -> dict[str, object]:
    return EffectivePolicyDecisionService().explain_policy_request(request)


@router.post("/contract-preview")
def contract_preview(request: PolicyResolveRequest):
    return EffectivePolicyDecisionService().contract_preview_for_policy_request(request)
