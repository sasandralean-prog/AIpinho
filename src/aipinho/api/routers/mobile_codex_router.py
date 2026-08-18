from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.services.codex_agent import CodexAgentService

router = APIRouter(prefix="/api/v1/mobile/codex", tags=["mobile-codex"])


@router.get("/view-model")
def mobile_codex_view_model(session_id: str, after_event_id: str | None = None) -> dict[str, object]:
    try:
        return CodexAgentService().mobile_view_model(session_id, after_event_id=after_event_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="codex_session_not_found") from exc
