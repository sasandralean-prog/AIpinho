from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.schemas.common.actor import Actor
from aipinho.schemas.common.base import AIpinhoModel
from aipinho.services.approvals.approval_task_continuation_service import ApprovalTaskContinuationService
from aipinho.services.approvals.approval_service import ApprovalService

router = APIRouter(prefix="/api/v1/approvals", tags=["approvals"])


class CreateApprovalRequest(AIpinhoModel):
    preview_id: str
    actions: list[str] | None = None
    actor: Actor | None = None
    reason: str = ""


class DecideApprovalRequest(AIpinhoModel):
    actor: Actor | None = None
    reason: str = ""
    scope: str = "single_action"


class BatchApprovalDecisionRequest(AIpinhoModel):
    approval_ids: list[str]
    actor: Actor | None = None
    reason: str = ""
    safe_only: bool = True


def _controlled_error(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=409, detail=str(exc))


@router.post("")
def create_approval(request: CreateApprovalRequest) -> dict[str, object]:
    try:
        approval = ApprovalService().create_approval_for_preview(request.preview_id, actions=request.actions, actor=request.actor, reason=request.reason)
        return {"status": "ok", "approval": approval}
    except ValueError as exc:
        raise _controlled_error(exc) from exc


@router.get("/pending")
def list_pending_approvals(limit: int = 100) -> dict[str, object]:
    approvals = ApprovalService().list_approvals(status="pending", limit=limit)
    return {"status": "ok", "approvals": [approval.model_dump() for approval in approvals]}


@router.post("/batch/approve")
def approve_approval_batch(request: BatchApprovalDecisionRequest) -> dict[str, object]:
    try:
        decisions = ApprovalService().approve_batch(
            request.approval_ids,
            actor=request.actor,
            reason=request.reason,
            safe_only=request.safe_only,
        )
        continuation = ApprovalTaskContinuationService()
        resume_results = [
            continuation.after_decision(approval, auto_process=False)
            for _decision, approval in decisions
        ]
        queue_process = continuation._process_queue_if_enabled()
        return {
            "status": "ok",
            "decisions": [decision.model_dump() for decision, _approval in decisions],
            "approvals": [approval.model_dump() for _decision, approval in decisions],
            "resume_results": resume_results,
            "queue_process": queue_process,
        }
    except ValueError as exc:
        raise _controlled_error(exc) from exc


@router.post("/batch/deny")
def deny_approval_batch(request: BatchApprovalDecisionRequest) -> dict[str, object]:
    try:
        decisions = ApprovalService().reject_batch(
            request.approval_ids,
            actor=request.actor,
            reason=request.reason,
            safe_only=request.safe_only,
        )
        continuation = ApprovalTaskContinuationService()
        resume_results = [
            continuation.after_decision(approval, auto_process=False)
            for _decision, approval in decisions
        ]
        queue_process = continuation._process_queue_if_enabled()
        return {
            "status": "ok",
            "decisions": [decision.model_dump() for decision, _approval in decisions],
            "approvals": [approval.model_dump() for _decision, approval in decisions],
            "resume_results": resume_results,
            "queue_process": queue_process,
        }
    except ValueError as exc:
        raise _controlled_error(exc) from exc


@router.post("/batch/reject")
def reject_approval_batch(request: BatchApprovalDecisionRequest) -> dict[str, object]:
    return deny_approval_batch(request)


@router.get("/{approval_id}")
def get_approval(approval_id: str) -> dict[str, object]:
    approval = ApprovalService().get_approval(approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="approval_not_found")
    return {"status": "ok", "approval": approval}


@router.get("/{approval_id}/events")
def get_approval_events(approval_id: str) -> dict[str, object]:
    service = ApprovalService()
    if service.get_approval(approval_id) is None:
        raise HTTPException(status_code=404, detail="approval_not_found")
    return {"status": "ok", "events": service.list_events(approval_id)}


@router.post("/{approval_id}/approve")
def approve_approval(approval_id: str, request: DecideApprovalRequest | None = None) -> dict[str, object]:
    try:
        decision, approval = ApprovalService().approve(
            approval_id,
            actor=request.actor if request else None,
            reason=request.reason if request else "",
            scope=request.scope if request else "single_action",
        )
        resume = ApprovalTaskContinuationService().after_decision(approval)
        return {"status": "ok", "decision": decision, "approval": approval, "resume": resume}
    except ValueError as exc:
        raise _controlled_error(exc) from exc


@router.post("/{approval_id}/reject")
def reject_approval(approval_id: str, request: DecideApprovalRequest | None = None) -> dict[str, object]:
    try:
        decision, approval = ApprovalService().reject(
            approval_id,
            actor=request.actor if request else None,
            reason=request.reason if request else "",
            scope=request.scope if request else "single_action",
        )
        resume = ApprovalTaskContinuationService().after_decision(approval)
        return {"status": "ok", "decision": decision, "approval": approval, "resume": resume}
    except ValueError as exc:
        raise _controlled_error(exc) from exc


@router.post("/{approval_id}/deny")
def deny_approval(approval_id: str, request: DecideApprovalRequest | None = None) -> dict[str, object]:
    return reject_approval(approval_id, request)


@router.post("/{approval_id}/cancel")
def cancel_approval(approval_id: str, request: DecideApprovalRequest | None = None) -> dict[str, object]:
    try:
        decision, approval = ApprovalService().cancel(
            approval_id,
            actor=request.actor if request else None,
            reason=request.reason if request else "",
            scope=request.scope if request else "single_action",
        )
        resume = ApprovalTaskContinuationService().after_decision(approval)
        return {"status": "ok", "decision": decision, "approval": approval, "resume": resume}
    except ValueError as exc:
        raise _controlled_error(exc) from exc


@router.post("/{approval_id}/refresh-policy")
def refresh_approval_policy(approval_id: str) -> dict[str, object]:
    approval = ApprovalService().refresh_policy(approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="approval_not_found")
    return {"status": "ok", "approval": approval}
