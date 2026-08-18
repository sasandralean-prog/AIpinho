from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.schemas.agents.delegation import DelegationCreateRequest
from aipinho.services.agents.agent_delegation_service import AgentDelegationService

router = APIRouter(prefix="/api/v1/agents", tags=["agent-delegation-contracts"])


def _service() -> AgentDelegationService:
    return AgentDelegationService()


@router.post("/{agent_id}/runs/{run_id}/delegate")
def create_delegation(agent_id: str, run_id: str, request: DelegationCreateRequest) -> dict[str, object]:
    try:
        response = _service().create_delegation(agent_id, run_id, request)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="agent_run_not_found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return response.model_dump()


@router.get("/delegations/{delegation_id}")
def get_delegation(delegation_id: str) -> dict[str, object]:
    try:
        return _service().get_delegation(delegation_id).model_dump()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="delegation_not_found") from exc


@router.get("/delegations/{delegation_id}/events")
def get_delegation_events(delegation_id: str, include_child_events: bool = False) -> dict[str, object]:
    service = _service()
    try:
        data = service.get_delegation(delegation_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="delegation_not_found") from exc
    parent_events = service.kernel.list_run_events(data.delegation.parent_run_id, include_hidden=True)
    events = [event for event in parent_events if event.delegation_id == delegation_id]
    if include_child_events and data.delegation.child_run_id:
        events.extend(event for event in service.kernel.list_run_events(data.delegation.child_run_id, include_hidden=True) if event.delegation_id == delegation_id)
    return {"status": "ok", "delegation_id": delegation_id, "events": [event.model_dump() for event in events]}


@router.get("/delegations/{delegation_id}/result")
def get_delegation_result(delegation_id: str) -> dict[str, object]:
    try:
        return {"status": "ok", "result": _service().result(delegation_id).model_dump()}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="delegation_result_not_found") from exc


@router.post("/delegations/{delegation_id}/cancel")
def cancel_delegation(delegation_id: str) -> dict[str, object]:
    try:
        return _service().cancel(delegation_id).model_dump()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="delegation_not_found") from exc


@router.post("/delegations/{delegation_id}/check-timeout")
def check_delegation_timeout(delegation_id: str) -> dict[str, object]:
    try:
        return _service().check_timeout(delegation_id).model_dump()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="delegation_not_found") from exc


@router.get("/runs/{run_id}/children")
def list_run_children(run_id: str) -> dict[str, object]:
    rows = _service().children(run_id)
    return {"status": "ok", "run_id": run_id, "children": [row.model_dump() for row in rows]}


@router.get("/runs/{run_id}/parent")
def get_run_parent(run_id: str) -> dict[str, object]:
    parent = _service().parent(run_id)
    return {"status": "ok", "run_id": run_id, "parent": parent.model_dump() if parent else None}
