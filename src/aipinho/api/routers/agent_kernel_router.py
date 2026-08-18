from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from aipinho.schemas.agents.contracts import AgentEventCreateRequest, AgentMessageCreateRequest, AgentSessionCreateRequest, AgentSessionUpdateRequest
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService

router = APIRouter(prefix="/api/v1/agents", tags=["agent-session-kernel"])
mobile_router = APIRouter(prefix="/api/v1/mobile/agents", tags=["mobile-agent-session-kernel"])


def _service() -> AgentSessionKernelService:
    return AgentSessionKernelService()


@router.get("/status")
def get_agents_status() -> dict[str, object]:
    return {"status": "ok", "registry": _service().profiles.status().model_dump()}


@router.get("/runs/{run_id}")
def get_agent_run(run_id: str) -> dict[str, object]:
    run = _service().get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="agent_run_not_found")
    return {"status": "ok", "run": run.model_dump()}


@router.get("/runs/{run_id}/events")
def get_agent_run_events(
    run_id: str,
    include_hidden: bool = False,
    after_event_id: str | None = None,
    after_sequence: int | None = None,
    limit: int = 200,
    mode: str = "normal",
) -> dict[str, object]:
    service = _service()
    try:
        response = service.run_events_response(
            run_id,
            include_hidden=include_hidden,
            after_event_id=after_event_id,
            after_sequence=after_sequence,
            limit=limit,
            mode=mode,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="agent_run_not_found") from exc
    return response.model_dump()


@router.get("")
def list_agents(enabled: bool | None = Query(default=None)) -> dict[str, object]:
    profiles = _service().list_profiles(enabled=enabled)
    return {"status": "ok", "agents": [profile.model_dump() for profile in profiles]}


@router.get("/{agent_id}")
def get_agent(agent_id: str) -> dict[str, object]:
    profile = _service().get_profile(agent_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="agent_profile_not_found")
    return {"status": "ok", "agent": profile.model_dump()}


@router.get("/{agent_id}/sessions")
def list_agent_sessions(agent_id: str, include_compat: bool = True) -> dict[str, object]:
    try:
        sessions = _service().list_sessions(agent_id, include_compat=include_compat)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="agent_profile_not_found") from exc
    return {"status": "ok", "agent_id": agent_id, "sessions": [session.model_dump() for session in sessions]}


@router.post("/{agent_id}/sessions")
def create_agent_session(agent_id: str, request: AgentSessionCreateRequest) -> dict[str, object]:
    try:
        session = _service().create_session(agent_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="agent_profile_not_found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"status": "ok", "session": session.model_dump()}


@router.get("/{agent_id}/sessions/{session_id}")
def get_agent_session(agent_id: str, session_id: str, include_compat: bool = True) -> dict[str, object]:
    try:
        session = _service().get_session(agent_id, session_id, include_compat=include_compat)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="agent_profile_not_found") from exc
    if session is None:
        raise HTTPException(status_code=404, detail="agent_session_not_found")
    state = _service().session_state(agent_id, session_id)
    return {"status": "ok", "session": session.model_dump(), "state": state.model_dump()}


@router.patch("/{agent_id}/sessions/{session_id}")
def update_agent_session(agent_id: str, session_id: str, request: AgentSessionUpdateRequest) -> dict[str, object]:
    try:
        session = _service().update_session(agent_id, session_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if session is None:
        raise HTTPException(status_code=404, detail="agent_session_not_found")
    return {"status": "ok", "session": session.model_dump()}


@router.delete("/{agent_id}/sessions/{session_id}")
def delete_agent_session(agent_id: str, session_id: str) -> dict[str, object]:
    session = _service().delete_session(agent_id, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="agent_session_not_found_or_compat_read_only")
    return {"status": "ok", "session": session.model_dump(), "deleted": True}


@router.get("/{agent_id}/sessions/{session_id}/messages")
def list_agent_messages(agent_id: str, session_id: str, include_raw_ref: bool = False) -> dict[str, object]:
    service = _service()
    if service.get_session(agent_id, session_id) is None:
        raise HTTPException(status_code=404, detail="agent_session_not_found")
    messages = service.list_messages(agent_id, session_id, include_raw_ref=include_raw_ref)
    return {"status": "ok", "agent_id": agent_id, "session_id": session_id, "messages": [message.model_dump() for message in messages]}


@router.post("/{agent_id}/sessions/{session_id}/messages")
def create_agent_message(agent_id: str, session_id: str, request: AgentMessageCreateRequest) -> dict[str, object]:
    service = _service()
    try:
        message = service.add_message(agent_id, session_id, request)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="agent_session_not_found") from exc
    public = service.list_messages(agent_id, session_id, include_raw_ref=False)[-1]
    return {"status": "ok", "message": public.model_dump(), "stored_message_id": message.message_id}


@router.post("/runs/{run_id}/events")
def create_agent_event(run_id: str, request: AgentEventCreateRequest) -> dict[str, object]:
    try:
        event = _service().add_event(run_id, request)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="agent_run_not_found") from exc
    return {"status": "ok", "event": event.model_dump()}


@router.get("/{agent_id}/sessions/{session_id}/timeline")
def get_agent_timeline(
    agent_id: str,
    session_id: str,
    after_event_id: str | None = None,
    after_sequence: int | None = None,
    limit: int = 200,
    include_hidden: bool = False,
    mode: str = "normal",
) -> dict[str, object]:
    try:
        response = _service().timeline_response(
            agent_id,
            session_id,
            after_event_id=after_event_id,
            after_sequence=after_sequence,
            limit=limit,
            include_hidden=include_hidden,
            mode=mode,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="agent_session_not_found") from exc
    return response.model_dump()


@mobile_router.get("/{agent_id}/view-model")
def get_mobile_agent_view_model(
    agent_id: str,
    session_id: str,
    after_event_id: str | None = None,
    mode: str = "normal",
) -> dict[str, object]:
    try:
        response = _service().mobile_view_model(agent_id, session_id, after_event_id=after_event_id, mode=mode)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="agent_session_not_found") from exc
    return response.model_dump()
