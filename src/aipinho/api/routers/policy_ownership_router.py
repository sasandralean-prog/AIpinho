from __future__ import annotations

from fastapi import APIRouter

from aipinho.services.policy.decision_ownership_service import DecisionOwnershipService

router = APIRouter(prefix="/api/v1/policy", tags=["policy-ownership"])


@router.get("/ownership")
def policy_ownership() -> dict[str, object]:
    return {"status": "ok", "matrix": DecisionOwnershipService().matrix().model_dump()}
