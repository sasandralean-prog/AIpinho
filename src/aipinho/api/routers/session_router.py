from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.services.session.session_service import SessionService

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


class CreateSessionRequest(AIpinhoModel):
    surface: str | None = None


@router.post("")
def create_session(request: CreateSessionRequest | None = None) -> dict[str, object]:
    state = SessionService().create_session(surface=request.surface if request else None)
    return {"status": "ok", "session": state}


@router.get("/{session_id}")
def get_session(session_id: str) -> dict[str, object]:
    state = SessionService().get_session(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="session_not_found")
    return {"status": "ok", "session": state}


@router.get("/{session_id}/events")
def get_session_events(session_id: str) -> dict[str, object]:
    service = SessionService()
    if service.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="session_not_found")
    return {"status": "ok", "events": service.list_events(session_id)}


@router.delete("/{session_id}")
def delete_session(session_id: str) -> dict[str, object]:
    deleted = SessionService().delete_session(session_id)
    return {"status": "ok" if deleted else "not_found", "deleted": deleted}