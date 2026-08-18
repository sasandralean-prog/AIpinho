from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.schemas.cognitive_governance import CognitiveEscalationRequest, CognitiveEvaluationRequest, CognitiveGovernanceRequest, CognitiveRoutingRequest
from aipinho.services.cognitive_policy_engine_service import CognitiveEscalationEngine, CognitiveGovernanceController, CognitivePolicyEngine, CognitiveRouter


router = APIRouter(prefix="/api/v1/runtime/cognitive", tags=["cognitive-governance"])


@router.get("/status")
def status() -> dict[str, object]:
    return CognitivePolicyEngine().status()


@router.get("/policies")
def list_policies() -> dict[str, object]:
    return CognitivePolicyEngine().list_policies().model_dump(mode="json")


@router.get("/policies/{policy_id}")
def get_policy(policy_id: str) -> dict[str, object]:
    policy = CognitivePolicyEngine().get_policy(policy_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="cognitive_policy_not_found")
    return policy.model_dump(mode="json")


@router.post("/evaluate")
def evaluate(request: CognitiveEvaluationRequest) -> dict[str, object]:
    return CognitivePolicyEngine().evaluate(request).model_dump(mode="json")


@router.post("/router")
def route(request: CognitiveRoutingRequest) -> dict[str, object]:
    return CognitiveRouter().route(request).model_dump(mode="json")


@router.get("/routes")
def routes() -> dict[str, object]:
    return CognitiveRouter().routes().model_dump(mode="json")


@router.post("/escalate")
def escalate(request: CognitiveEscalationRequest) -> dict[str, object]:
    return CognitiveEscalationEngine().escalate(request).model_dump(mode="json")


@router.get("/escalation-history")
def escalation_history() -> dict[str, object]:
    return CognitiveEscalationEngine().history().model_dump(mode="json")


@router.get("/governance")
def governance_status() -> dict[str, object]:
    return CognitiveGovernanceController().status()


@router.post("/governance/evaluate")
def governance_evaluate(request: CognitiveGovernanceRequest) -> dict[str, object]:
    return CognitiveGovernanceController().evaluate(request).model_dump(mode="json")


@router.get("/governance/history")
def governance_history() -> dict[str, object]:
    return CognitiveGovernanceController().history().model_dump(mode="json")
