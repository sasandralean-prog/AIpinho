from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from aipinho.schemas.agents.memory import (
    MemoryCandidateCreateRequest,
    MemoryCandidateReviewRequest,
    MemoryContextLoadRequest,
    MemorySearchRequest,
    MemorySupersedeRequest,
    MemoryWriteRequest,
)
from aipinho.services.agents.agent_memory_gateway_service import AgentMemoryGatewayService

router = APIRouter(prefix="/api/v1/agents/memory", tags=["multi-agent-memory-gateway"])


def _service() -> AgentMemoryGatewayService:
    return AgentMemoryGatewayService()


@router.get("/status")
def status() -> dict[str, Any]:
    return _service().status()


@router.get("/namespaces")
def namespaces() -> dict[str, Any]:
    return {"status": "ok", "namespaces": [item.model_dump() for item in _service().namespaces()]}


@router.get("/{namespace}/records")
def list_records(namespace: str, agent_id: str, limit: int = Query(default=100, ge=1, le=1000)) -> dict[str, Any]:
    service = _service()
    request = MemorySearchRequest(agent_id=agent_id, namespaces=[namespace], limit=limit)  # type: ignore[list-item]
    result = service.search(request)
    return result.model_dump()


@router.post("/{namespace}/records")
def write_record(namespace: str, request: MemoryWriteRequest) -> dict[str, Any]:
    if request.namespace != namespace:
        request = request.model_copy(update={"namespace": namespace})
    return _service().write_memory(request).model_dump()


@router.get("/records/{memory_id}")
def get_record(memory_id: str) -> dict[str, Any]:
    memory = _service().store.get_record(memory_id)
    if memory is None:
        raise HTTPException(status_code=404, detail="memory_not_found")
    return {"status": memory.validation_status, "memory": memory.model_dump()}


@router.patch("/records/{memory_id}")
def patch_record(memory_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    service = _service()
    agent_id = str(payload.get("agent_id") or "aipinho")
    try:
        updated, policy = service.update_record(memory_id, payload, agent_id=agent_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="memory_not_found")
    except PermissionError as exc:
        raise HTTPException(status_code=400, detail={"error": "memory_update_blocked", "reason": str(exc)}) from exc
    return {"status": updated.validation_status, "policy": policy.model_dump(), "memory": updated.model_dump()}


@router.post("/search")
def search(request: MemorySearchRequest) -> dict[str, Any]:
    return _service().search(request).model_dump()


@router.post("/candidates")
def create_candidate(request: MemoryCandidateCreateRequest) -> dict[str, Any]:
    return {"status": "pending", "candidate": _service().create_candidate(request).model_dump()}


@router.get("/candidates")
def list_candidates(status: str | None = None, namespace: str | None = None, agent_id: str | None = None) -> dict[str, Any]:
    rows = _service().store.list_candidates(namespace=namespace, proposed_by_agent_id=agent_id, status=status)
    return {"status": "ok", "candidates": [row.model_dump() for row in rows]}


@router.post("/candidates/{candidate_id}/accept")
def accept_candidate(candidate_id: str, request: MemoryCandidateReviewRequest) -> dict[str, Any]:
    try:
        return _service().accept_candidate(candidate_id, request).model_dump()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="memory_candidate_not_found") from exc


@router.post("/candidates/{candidate_id}/reject")
def reject_candidate(candidate_id: str, request: MemoryCandidateReviewRequest) -> dict[str, Any]:
    try:
        candidate = _service().reject_candidate(candidate_id, request)
        return {"status": candidate.status, "candidate": candidate.model_dump()}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="memory_candidate_not_found") from exc


@router.post("/records/{memory_id}/supersede")
def supersede(memory_id: str, request: MemorySupersedeRequest) -> dict[str, Any]:
    try:
        memory = _service().supersede(memory_id, request)
        return {"status": memory.validation_status, "memory": memory.model_dump()}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="memory_not_found") from exc


@router.get("/agents/{agent_id}/context")
def agent_context(agent_id: str, session_id: str | None = None, run_id: str | None = None, workspace_id: str | None = None, project_id: str | None = None) -> dict[str, Any]:
    return _service().load_context_for_run(
        MemoryContextLoadRequest(agent_id=agent_id, session_id=session_id, run_id=run_id, workspace_id=workspace_id, project_id=project_id)
    ).model_dump()


@router.get("/runs/{run_id}")
def run_memory(run_id: str) -> dict[str, Any]:
    try:
        return _service().run_memory(run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="agent_run_not_found") from exc
