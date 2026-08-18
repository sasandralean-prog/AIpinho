from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.schemas.multi_agent_observability import DebugBundleExportRequest
from aipinho.services.agents.multi_agent_observability_service import MultiAgentObservabilityService

router = APIRouter(prefix="/api/v1/debugger", tags=["multi-agent-debugger"])


def _service() -> MultiAgentObservabilityService:
    return MultiAgentObservabilityService()


@router.get("/events")
def list_debugger_events(
    agent_id: str | None = None,
    session_id: str | None = None,
    run_id: str | None = None,
    delegation_id: str | None = None,
    tool_invocation_id: str | None = None,
    policy_decision_id: str | None = None,
    approval_id: str | None = None,
    artifact_id: str | None = None,
    validation_id: str | None = None,
    memory_id: str | None = None,
    event_type: str | None = None,
    status: str | None = None,
    severity: str | None = None,
    cursor: str | None = None,
    include_hidden: bool = False,
    mode: str = "normal",
    text: str | None = None,
    limit: int = 200,
) -> dict[str, object]:
    return _service().debugger_events(
        agent_id=agent_id,
        session_id=session_id,
        run_id=run_id,
        delegation_id=delegation_id,
        tool_invocation_id=tool_invocation_id,
        policy_decision_id=policy_decision_id,
        approval_id=approval_id,
        artifact_id=artifact_id,
        validation_id=validation_id,
        memory_id=memory_id,
        event_type=event_type,
        status=status,
        severity=severity,
        cursor=cursor,
        include_hidden=include_hidden,
        mode=mode,
        text=text,
        limit=limit,
    ).model_dump()


@router.get("/entities/{entity_type}/{entity_id}")
def get_debugger_entity(entity_type: str, entity_id: str) -> dict[str, object]:
    try:
        return _service().entity(entity_type, entity_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="debugger_entity_not_found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/export")
def export_debug_bundle(request: DebugBundleExportRequest) -> dict[str, object]:
    return _service().export_debug_bundle(request).model_dump()


@router.get("/filters")
def debugger_filters() -> dict[str, object]:
    return _service().filters()
