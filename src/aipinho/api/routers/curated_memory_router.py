from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from aipinho.schemas.memory.curated_memory import CuratedMemoryRequest, MemoryExpirationRequest, MemorySearchRequest, MemorySupersedeRequest
from aipinho.services.memory.curated_memory_service import CuratedMemoryService

router = APIRouter(prefix="/api/v1/memory/curated", tags=["curated-memory"])


@router.get("/status")
def curated_memory_status() -> dict[str, Any]:
    return CuratedMemoryService().status()


@router.post("/from-candidate/{candidate_id}")
def persist_from_candidate(candidate_id: str, request: CuratedMemoryRequest) -> dict[str, Any]:
    if request.candidate_id != candidate_id:
        raise HTTPException(status_code=409, detail="candidate_id_mismatch")
    return CuratedMemoryService().persist_from_candidate(request).model_dump()


@router.get("/{memory_id}")
def get_memory(memory_id: str) -> dict[str, Any]:
    memory = CuratedMemoryService().get_memory(memory_id)
    if memory is None:
        raise HTTPException(status_code=404, detail="curated_memory_not_found")
    return {"status": memory.status, "memory": memory}


@router.get("/{memory_id}/versions")
def get_memory_versions(memory_id: str) -> dict[str, Any]:
    service = CuratedMemoryService()
    if service.get_memory(memory_id) is None:
        raise HTTPException(status_code=404, detail="curated_memory_not_found")
    return {"status": "ok", "memory_id": memory_id, "versions": service.store.get_versions(memory_id)}


@router.get("/{memory_id}/evidence")
def get_memory_evidence(memory_id: str) -> dict[str, Any]:
    memory = CuratedMemoryService().get_memory(memory_id)
    if memory is None:
        raise HTTPException(status_code=404, detail="curated_memory_not_found")
    return {"status": "ok", "memory_id": memory_id, "evidence": memory.evidence}


@router.get("/{memory_id}/trace")
def get_memory_trace(memory_id: str) -> dict[str, Any]:
    service = CuratedMemoryService()
    if service.get_memory(memory_id) is None:
        raise HTTPException(status_code=404, detail="curated_memory_not_found")
    return {"status": "ok", "memory_id": memory_id, "trace": service.store.get_trace(memory_id)}


@router.get("/{memory_id}/events")
def get_memory_events(memory_id: str) -> dict[str, Any]:
    service = CuratedMemoryService()
    if service.get_memory(memory_id) is None:
        raise HTTPException(status_code=404, detail="curated_memory_not_found")
    return {"status": "ok", "memory_id": memory_id, "events": service.store.get_events(memory_id)}


@router.post("/{memory_id}/supersede")
def supersede_memory(memory_id: str, request: MemorySupersedeRequest) -> dict[str, Any]:
    result = CuratedMemoryService().supersede(memory_id, request)
    if result is None:
        raise HTTPException(status_code=409, detail="supersede_blocked")
    return result.model_dump()


@router.post("/{memory_id}/expire")
def expire_memory(memory_id: str, request: MemoryExpirationRequest) -> dict[str, Any]:
    memory = CuratedMemoryService().expire(memory_id, request)
    if memory is None:
        raise HTTPException(status_code=409, detail="expire_blocked")
    return {"status": memory.status, "memory": memory}


@router.post("/{memory_id}/reject")
def reject_memory(memory_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    memory = CuratedMemoryService().reject(memory_id, str((payload or {}).get("reason") or "rejected"))
    if memory is None:
        raise HTTPException(status_code=404, detail="curated_memory_not_found")
    return {"status": memory.status, "memory": memory}


@router.post("/search")
def search_memory(request: MemorySearchRequest) -> dict[str, Any]:
    return CuratedMemoryService().search(request).model_dump()


@router.get("")
def list_curated_memories(
    status: str | None = None,
    kind: str | None = None,
    scope: str | None = None,
    workspace: str | None = None,
    source_type: str | None = None,
    confidence: str | None = None,
    risk: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
) -> dict[str, Any]:
    memories = CuratedMemoryService().list_memories(status=status, kind=kind, scope=scope, workspace=workspace, source_type=source_type, confidence=confidence, risk=risk, limit=limit)
    return {"status": "ok", "memories": memories}
