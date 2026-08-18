from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.services.agents.multi_agent_policy_kernel_service import MultiAgentPolicyKernelService


router = APIRouter(prefix="/api/v1/agents/policy-kernel", tags=["multi-agent-policy-kernel"])


def _service() -> MultiAgentPolicyKernelService:
    return MultiAgentPolicyKernelService()


@router.get("/status")
def policy_kernel_status() -> dict[str, object]:
    return _service().status().model_dump()


@router.get("/block-reason-codes")
def list_block_reason_codes() -> dict[str, object]:
    reasons = _service()._block_reasons()
    return {"status": "ok", "block_reason_codes": [reason.model_dump() for reason in reasons.values()]}


@router.get("/decisions/{policy_decision_id}")
def get_policy_decision(policy_decision_id: str) -> dict[str, object]:
    decision = _service().store.get_policy_decision(policy_decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="policy_decision_not_found")
    return {"status": "ok", "policy_decision": decision.model_dump()}
