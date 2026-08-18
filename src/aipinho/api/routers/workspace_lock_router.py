from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.schemas.agents.ownership import (
    AgentHopCheckRequest,
    WorkspaceLockCreateRequest,
    WorkspaceLockOverrideRequest,
    WorkspaceLockReleaseRequest,
    WriteConflictCheckRequest,
)
from aipinho.services.agents.workspace_lock_service import WorkspaceLockService

router = APIRouter(prefix="/api/v1/locks", tags=["workspace-locks"])


def _service() -> WorkspaceLockService:
    return WorkspaceLockService()


@router.get("")
def list_locks(include_inactive: bool = False) -> dict[str, object]:
    return {"status": "ok", "locks": [lock.model_dump() for lock in _service().list(include_inactive=include_inactive)]}


@router.post("")
def create_lock(request: WorkspaceLockCreateRequest) -> dict[str, object]:
    return {"status": "ok", "lock": _service().create(request).model_dump()}


@router.get("/by-workspace")
def locks_by_workspace(workspace: str, include_inactive: bool = False) -> dict[str, object]:
    return {"status": "ok", "workspace": workspace, "locks": [lock.model_dump() for lock in _service().by_workspace(workspace, include_inactive=include_inactive)]}


@router.post("/check-write")
def check_write_conflict(request: WriteConflictCheckRequest) -> dict[str, object]:
    decision = _service().check_write_conflict(request)
    return {"status": decision.status, "decision": decision.model_dump()}


@router.post("/check-hop")
def check_hop(request: AgentHopCheckRequest) -> dict[str, object]:
    decision = _service().check_hop(request)
    return {"status": "ok" if decision.allowed else "blocked", "decision": decision.model_dump()}


@router.post("/{lock_id}/release")
def release_lock(lock_id: str, request: WorkspaceLockReleaseRequest | None = None) -> dict[str, object]:
    try:
        lock = _service().release(lock_id, request or WorkspaceLockReleaseRequest())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="lock_not_found") from exc
    return {"status": "ok", "lock": lock.model_dump()}


@router.post("/{lock_id}/override")
def override_lock(lock_id: str, request: WorkspaceLockOverrideRequest) -> dict[str, object]:
    try:
        lock = _service().override(lock_id, request)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="lock_not_found") from exc
    return {"status": "ok", "lock": lock.model_dump()}

