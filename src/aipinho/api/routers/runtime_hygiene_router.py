from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from aipinho.services.runtime.runtime_state_hygiene_service import RuntimeStateHygieneService

router = APIRouter(prefix="/api/v1/runtime/hygiene", tags=["runtime-hygiene"])


@router.get("/status")
def runtime_hygiene_status() -> dict[str, object]:
    return RuntimeStateHygieneService().status()


@router.get("/queue-health")
def runtime_hygiene_queue_health(
    max_age_hours: int = Query(default=1, ge=1, le=24 * 365),
    worker_pool_capacity: int = Query(default=8, ge=1, le=256),
) -> dict[str, object]:
    return RuntimeStateHygieneService().queue_health(max_age_hours=max_age_hours, worker_pool_capacity=worker_pool_capacity)


@router.post("/preview")
def runtime_hygiene_preview(
    max_age_hours: int = Query(default=24, ge=1, le=24 * 365),
    limit: int = Query(default=200, ge=1, le=2000),
    kinds: str | None = Query(default=None, description="Comma-separated candidate kinds: run,session,delegation"),
) -> dict[str, object]:
    selected = [item.strip() for item in kinds.split(",")] if kinds else None
    try:
        return RuntimeStateHygieneService().preview(max_age_hours=max_age_hours, limit=limit, kinds=selected)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/apply/{preview_id}")
def runtime_hygiene_apply(preview_id: str) -> dict[str, object]:
    try:
        return RuntimeStateHygieneService().apply(preview_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="cleanup_preview_not_found") from exc
