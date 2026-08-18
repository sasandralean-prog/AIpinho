from __future__ import annotations

import json
from fastapi import APIRouter
from starlette.responses import StreamingResponse

from aipinho.services.realtime.event_stream_service import EventStreamService
from aipinho.services.realtime.realtime_core import RealtimeEventBus
from aipinho.services.realtime.realtime_status_service import RealtimeStatusService
from aipinho.services.realtime.sync_heartbeat_service import SyncHeartbeatService

router = APIRouter(prefix="/api/v1/realtime", tags=["realtime"])


@router.get("/status")
def realtime_status() -> dict[str, object]:
    status = RealtimeStatusService().status()
    status.update(RealtimeEventBus().status())
    return status


@router.get("/heartbeat")
def realtime_heartbeat() -> dict[str, object]:
    return SyncHeartbeatService().heartbeat()


@router.get("/events/since/{cursor}")
def realtime_events_since(cursor: str, limit: int = 100) -> dict[str, object]:
    return {"status": "ok", "cursor": cursor, "events": [change.model_dump() for change in RealtimeEventBus().changes(cursor, limit=limit)]}


@router.get("/events/stream")
def realtime_events_stream(cursor: str | None = None):
    def gen():
        changes = RealtimeEventBus().changes(cursor, limit=100)
        if not changes:
            yield EventStreamService().status_event()
            return
        for change in changes:
            yield f"id: {change.cursor}\nevent: change\ndata: {json.dumps(change.model_dump(), ensure_ascii=True)}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")
