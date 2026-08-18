from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from aipinho.schemas.memory.curated_memory import CuratedMemoryRequest, MemoryApprovalRequest
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.memory.curated_memory_service import CuratedMemoryService
from aipinho.services.memory.memory_approval_service import MemoryApprovalService

router = APIRouter(prefix="/api/v1/memory/approvals", tags=["memory-approvals"])


@router.post("/from-candidate/{candidate_id}")
def request_memory_approval(candidate_id: str, request: MemoryApprovalRequest | None = None) -> dict[str, Any]:
    request = request or MemoryApprovalRequest(candidate_id=candidate_id)
    if request.candidate_id != candidate_id:
        raise HTTPException(status_code=409, detail="candidate_id_mismatch")
    result = MemoryApprovalService().request_from_candidate(candidate_id, reason=request.reason, operator_confirmed=request.operator_confirmed)
    return result.model_dump()


@router.post("/{approval_id}/persist")
def persist_memory_approval(approval_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    candidate_id = payload.get("candidate_id")
    approval = ApprovalService().get_approval(approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="approval_not_found")
    if not candidate_id:
        candidate_id = (approval.policy_snapshot.config_versions.get("memory", {}) or {}).get("candidate_id")
    if not candidate_id:
        raise HTTPException(status_code=409, detail="candidate_id_missing")
    result = CuratedMemoryService().persist_from_candidate(
        CuratedMemoryRequest(
            candidate_id=str(candidate_id),
            approval_id=approval_id,
            operator_confirmed=bool(payload.get("operator_confirmed", False)),
            resolution=payload.get("resolution"),
            supersede_memory_id=payload.get("supersede_memory_id"),
            reason=str(payload.get("reason") or ""),
        )
    )
    return result.model_dump()
