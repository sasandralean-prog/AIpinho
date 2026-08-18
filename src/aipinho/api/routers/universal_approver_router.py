from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from aipinho.schemas.approvals.universal_approver import UniversalApprovalTextRequest, UniversalApproverUpsertRequest
from aipinho.services.approvals.universal_approver_service import UniversalApproverService

router = APIRouter(prefix="/api/v1/universal-approvers", tags=["universal-approvers"])


def _service() -> UniversalApproverService:
    return UniversalApproverService()


@router.get("")
def list_universal_approvers() -> dict[str, object]:
    approvers = _service().list_approvers()
    return {"status": "ok", "authority": "AIpinho", "approvers": [item.model_dump() for item in approvers]}


@router.post("")
def upsert_universal_approver(request: UniversalApproverUpsertRequest) -> dict[str, object]:
    approver = _service().upsert_approver(request)
    return {"status": "ok", "authority": "AIpinho", "approver": approver.model_dump()}


@router.get("/mobile-view")
def universal_approver_mobile_view() -> dict[str, object]:
    return _service().mobile_view_model()


@router.get("/approval-timeline")
def universal_approval_timeline(limit: int = Query(default=100, ge=1, le=1000)) -> dict[str, object]:
    return _service().timeline(limit=limit)


@router.get("/{approver_id}")
def get_universal_approver(approver_id: str) -> dict[str, object]:
    approver = _service().get_approver(approver_id)
    if approver is None:
        raise HTTPException(status_code=404, detail="universal_approver_not_found")
    return {"status": "ok", "authority": "AIpinho", "approver": approver.model_dump()}


@router.post("/approvals/{approval_id}/text-decision")
def decide_approval_from_text(approval_id: str, request: UniversalApprovalTextRequest) -> dict[str, object]:
    result = _service().decide_from_text(approval_id, request)
    if result.status == "blocked":
        return result.model_dump()
    return result.model_dump()
