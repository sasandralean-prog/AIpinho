from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.services.orchestration.task_contract_draft_service import TaskContractDraftService
from aipinho.services.session.session_service import SessionService

router = APIRouter(prefix="/api/v1/task-drafts", tags=["task-drafts"])


class CreateTaskDraftRequest(AIpinhoModel):
    prompt: str
    session_id: str | None = None


@router.post("")
def create_task_draft(request: CreateTaskDraftRequest) -> dict[str, object]:
    session_state = SessionService().get_session(request.session_id) if request.session_id else None
    draft = TaskContractDraftService().create_from_prompt(request.prompt, session_state=session_state)
    if draft is None:
        return {"status": "not_applicable", "draft": None, "reason": "intent_does_not_create_task_draft"}
    return {"status": "ok", "draft": draft}


@router.get("/{draft_id}")
def get_task_draft(draft_id: str) -> dict[str, object]:
    draft = TaskContractDraftService().get_draft(draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="task_draft_not_found")
    return {"status": "ok", "draft": draft}


@router.get("/{draft_id}/events")
def get_task_draft_events(draft_id: str) -> dict[str, object]:
    service = TaskContractDraftService()
    if service.get_draft(draft_id) is None:
        raise HTTPException(status_code=404, detail="task_draft_not_found")
    return {"status": "ok", "events": service.list_events(draft_id)}


@router.post("/{draft_id}/refresh-policy")
def refresh_task_draft_policy(draft_id: str) -> dict[str, object]:
    draft = TaskContractDraftService().refresh_policy(draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="task_draft_not_found")
    return {"status": "ok", "draft": draft}


@router.delete("/{draft_id}")
def delete_task_draft(draft_id: str) -> dict[str, object]:
    deleted = TaskContractDraftService().delete_draft(draft_id)
    return {"status": "ok" if deleted else "not_found", "deleted": deleted}