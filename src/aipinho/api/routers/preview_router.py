from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.services.orchestration.task_preview_service import TaskPreviewService

router = APIRouter(prefix="/api/v1/previews", tags=["previews"])


class CreatePreviewRequest(AIpinhoModel):
    draft_id: str


@router.post("")
def create_preview(request: CreatePreviewRequest) -> dict[str, object]:
    preview = TaskPreviewService().create_preview_from_draft(request.draft_id)
    if preview is None:
        raise HTTPException(status_code=404, detail="draft_not_found")
    return {"status": "ok", "preview": preview}


@router.post("/from-draft/{draft_id}")
def create_preview_from_draft(draft_id: str) -> dict[str, object]:
    preview = TaskPreviewService().create_preview_from_draft(draft_id)
    if preview is None:
        raise HTTPException(status_code=404, detail="draft_not_found")
    return {"status": "ok", "preview": preview}


@router.get("/{preview_id}")
def get_preview(preview_id: str) -> dict[str, object]:
    preview = TaskPreviewService().get_preview(preview_id)
    if preview is None:
        raise HTTPException(status_code=404, detail="preview_not_found")
    return {"status": "ok", "preview": preview}


@router.get("/{preview_id}/events")
def get_preview_events(preview_id: str) -> dict[str, object]:
    service = TaskPreviewService()
    if service.get_preview(preview_id) is None:
        raise HTTPException(status_code=404, detail="preview_not_found")
    return {"status": "ok", "events": service.list_events(preview_id)}


@router.post("/{preview_id}/refresh-policy")
def refresh_preview_policy(preview_id: str) -> dict[str, object]:
    preview = TaskPreviewService().refresh_policy(preview_id)
    if preview is None:
        raise HTTPException(status_code=404, detail="preview_not_found")
    return {"status": "ok", "preview": preview}