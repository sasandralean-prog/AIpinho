from __future__ import annotations

from typing import Any

from aipinho.schemas.realtime.contracts import ClientPresence, RealtimeEvent, SyncChange, SyncSnapshot
from aipinho.services.events.event_core import EventPublicPayloadBuilder, EventStoreRepository, redact_payload
from aipinho.services.interaction.interaction_core import ChatSessionService, PipelineSyncService, TaskSyncService


def _dump_model(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value.dict()


class RealtimeEventStore:
    def list(self, limit: int = 100, since_cursor: str | None = None) -> list[RealtimeEvent]:
        store = EventStoreRepository()
        builder = EventPublicPayloadBuilder()
        events = store.list(limit=limit, since_cursor=since_cursor)
        start = int(since_cursor) if since_cursor and since_cursor.isdigit() else 0
        return [RealtimeEvent(event=builder.build(event), cursor=str(start + index + 1)) for index, event in enumerate(events)]


class RealtimeEventBus:
    def status(self) -> dict[str, object]:
        return {"status": "ok", "cursor": EventStoreRepository().cursor(), "sse_enabled": True, "backend_sync_source": True}

    def changes(self, since_cursor: str | None = None, limit: int = 100) -> list[SyncChange]:
        return [SyncChange(cursor=item.cursor, kind="event", item=_dump_model(item.event)) for item in RealtimeEventStore().list(limit=limit, since_cursor=since_cursor)]


class SyncSnapshotService:
    def snapshot(self) -> SyncSnapshot:
        store = EventStoreRepository()
        events = [EventPublicPayloadBuilder().build(event).model_dump() for event in store.list(limit=200)]
        sessions = [session.model_dump() for session in ChatSessionService().list()]
        tasks = [card.model_dump() for card in TaskSyncService().list_cards()]
        pipeline = []
        for card in tasks:
            pipeline.append(PipelineSyncService().card(str(card["task_id"])).model_dump())
        return SyncSnapshot(cursor=store.cursor(), events=events, chat_sessions=sessions, tasks=tasks, pipeline=pipeline)


class SyncCursorService:
    def current(self) -> dict[str, object]:
        return {"cursor": EventStoreRepository().cursor(), "monotonic": True}


class ClientPresenceService:
    def update(self, client_id: str, surface: str) -> ClientPresence:
        return ClientPresence(client_id=client_id, surface=surface)


class SSEStreamService:
    def render(self, since_cursor: str | None = None) -> str:
        lines: list[str] = []
        for change in RealtimeEventBus().changes(since_cursor=since_cursor):
            lines.append(f"id: {change.cursor}")
            lines.append("event: change")
            lines.append(f"data: {redact_payload(change.model_dump())}")
            lines.append("")
        return "\n".join(lines)
