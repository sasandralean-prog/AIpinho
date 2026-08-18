from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.lucio_agent import LucioAgentRequest
from aipinho.services.lucio_agent import LucioAgentService


router = APIRouter(prefix="/api/v1/lucio-agent", tags=["lucio-agent"])


class CreateLucioSessionRequest(AIpinhoModel):
    title: str = "Lucio"


class RenameLucioSessionRequest(AIpinhoModel):
    title: str


@router.get("/health")
def health() -> dict[str, object]:
    return LucioAgentService().health()


@router.get("/config/status")
def config_status() -> dict[str, object]:
    return {"status": "ok", "config": LucioAgentService().config_service.status().model_dump()}


@router.post("/sessions")
def create_session(request: CreateLucioSessionRequest | None = None) -> dict[str, object]:
    service = LucioAgentService()
    if not service.config_service.runtime().allow_new_sessions:
        return service.disabled_payload()
    session = service.create_session(request.title if request else "Lucio")
    return {"status": "ok", "session": session.model_dump()}


@router.get("/sessions")
def list_sessions() -> dict[str, object]:
    sessions = LucioAgentService().sessions()
    return {"status": "ok", "sessions": [session.model_dump() for session in sessions], "total": len(sessions)}


@router.get("/sessions/{session_id}")
def get_session(session_id: str) -> dict[str, object]:
    session = LucioAgentService().get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="lucio_session_not_found")
    return {"status": "ok", "session": session.model_dump()}


@router.patch("/sessions/{session_id}")
def rename_session(session_id: str, request: RenameLucioSessionRequest) -> dict[str, object]:
    try:
        session = LucioAgentService().rename_session(session_id, request.title)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if session is None:
        raise HTTPException(status_code=404, detail="lucio_session_not_found")
    return {"status": "ok", "session": session.model_dump()}


@router.post("/sessions/{session_id}/rename")
def rename_session_compat(session_id: str, request: RenameLucioSessionRequest) -> dict[str, object]:
    return rename_session(session_id, request)


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str) -> dict[str, object]:
    session = LucioAgentService().delete_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="lucio_session_not_found")
    return {"status": "ok", "deleted": True, "session": session.model_dump()}


@router.get("/sessions/{session_id}/messages")
def messages(session_id: str) -> dict[str, object]:
    try:
        rows = LucioAgentService().messages(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="lucio_session_not_found") from exc
    return {"status": "ok", "messages": [row.model_dump() for row in rows]}


@router.post("/sessions/{session_id}/route-preview")
def route_preview(session_id: str, request: LucioAgentRequest) -> dict[str, object]:
    service = LucioAgentService()
    if not service.config_service.runtime().enabled:
        return service.disabled_payload(session_id=session_id)
    if service.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="lucio_session_not_found")
    decision = service.route_preview(request.model_copy(update={"session_id": session_id}))
    return {"status": "ok", "route_decision": decision.model_dump()}


@router.post("/sessions/{session_id}/send")
def send(session_id: str, request: LucioAgentRequest) -> dict[str, object]:
    service = LucioAgentService()
    if not service.config_service.runtime().enabled:
        return service.disabled_payload(session_id=session_id)
    try:
        response = service.send(request.model_copy(update={"session_id": session_id}))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="lucio_session_not_found") from exc
    return {"status": "ok", "response": response.model_dump()}


@router.get("/sessions/{session_id}/view-model")
def view_model(
    session_id: str,
    after_event_id: str | None = None,
    mode: str = Query(default="normal", pattern="^(normal|details|raw)$"),
) -> dict[str, object]:
    try:
        model = LucioAgentService().kernel.mobile_view_model(
            "lucio",
            session_id,
            after_event_id=after_event_id,
            mode=mode,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="lucio_session_not_found") from exc
    return model.model_dump()


@router.get("/runs/{run_id}/events")
def run_events(
    run_id: str,
    after_event_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, object]:
    service = LucioAgentService()
    run = service.kernel.get_run(run_id)
    if run is None or run.agent_id != "lucio":
        raise HTTPException(status_code=404, detail="lucio_run_not_found")
    rows = service.kernel.list_run_events(run_id, after_event_id=after_event_id, limit=limit)
    return {"status": "ok", "run_id": run_id, "events": [row.model_dump() for row in rows]}


@router.post("/runs/{run_id}/cancel")
def cancel_run(run_id: str) -> dict[str, object]:
    try:
        return LucioAgentService().cancel_run(run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="lucio_run_not_found") from exc
