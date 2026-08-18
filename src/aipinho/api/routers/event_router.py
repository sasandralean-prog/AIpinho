from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException

from aipinho.schemas.events.contracts import EventPublishRequest
from aipinho.services.security.local_token_service import LocalTokenService
from aipinho.services.events.event_core import EventCopyPolicyService, EventPublicPayloadBuilder, EventPublisherService, EventRawPayloadStore, EventStoreRepository, EventTraceService

router = APIRouter(prefix="/api/v1/events", tags=["events"])


@router.post("/publish")
def publish_event(request: EventPublishRequest) -> dict[str, object]:
    try:
        event = EventPublisherService().publish(request)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"status": "ok", "event": EventPublicPayloadBuilder().build(event).model_dump()}


@router.get("")
def list_events(limit: int = 100, since_cursor: str | None = None) -> dict[str, object]:
    builder = EventPublicPayloadBuilder()
    return {"status": "ok", "cursor": EventStoreRepository().cursor(), "events": [builder.build(event).model_dump() for event in EventStoreRepository().list(limit=limit, since_cursor=since_cursor)]}


@router.get("/{event_id}/copy")
def copy_event(event_id: str) -> dict[str, object]:
    try:
        return {"status": "ok", "copy": EventCopyPolicyService().copy(event_id).model_dump()}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="event_not_found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{event_id}/trace")
def trace_event(event_id: str) -> dict[str, object]:
    try:
        return EventTraceService().trace(event_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="event_not_found") from exc


@router.get("/{event_id}")
def get_event(event_id: str) -> dict[str, object]:
    event = EventStoreRepository().get(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="event_not_found")
    return {"status": "ok", "event": EventPublicPayloadBuilder().build(event).model_dump()}


@router.get("/{event_id}/raw")
def get_event_raw(event_id: str, authorization: str | None = Header(default=None)) -> dict[str, object]:
    event = EventStoreRepository().get(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="event_not_found")
    if not event.raw_ref:
        raise HTTPException(status_code=404, detail="raw_payload_not_found")
    if not LocalTokenService().validate_authorization(authorization):
        raise HTTPException(status_code=401, detail="local_token_required")
    return {"status": "ok", "raw": EventRawPayloadStore().read(event.raw_ref)}

