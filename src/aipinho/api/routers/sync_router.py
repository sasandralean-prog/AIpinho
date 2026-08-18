from __future__ import annotations

from fastapi import APIRouter

from aipinho.services.realtime.realtime_core import RealtimeEventBus, SyncCursorService, SyncSnapshotService

router = APIRouter(prefix="/api/v1/sync", tags=["sync"])


@router.get("/snapshot")
def sync_snapshot() -> dict[str, object]:
    return {"status": "ok", "snapshot": SyncSnapshotService().snapshot().model_dump()}


@router.get("/changes")
def sync_changes(cursor: str | None = None, limit: int = 100) -> dict[str, object]:
    return {"status": "ok", "cursor": SyncCursorService().current(), "changes": [change.model_dump() for change in RealtimeEventBus().changes(cursor, limit=limit)]}
