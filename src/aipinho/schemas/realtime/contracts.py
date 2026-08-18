from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import PublicEventPayload, utc_now_iso


class RealtimeEvent(AIpinhoModel):
    realtime_id: str = Field(default_factory=lambda: f"rt_{uuid4().hex}")
    event: PublicEventPayload
    cursor: str
    created_at: str = Field(default_factory=utc_now_iso)


class SyncCursor(AIpinhoModel):
    cursor: str = "0"


class SyncChange(AIpinhoModel):
    cursor: str
    kind: str
    item: dict[str, Any]


class SyncSnapshot(AIpinhoModel):
    cursor: str
    events: list[dict[str, Any]] = Field(default_factory=list)
    chat_sessions: list[dict[str, Any]] = Field(default_factory=list)
    tasks: list[dict[str, Any]] = Field(default_factory=list)
    pipeline: list[dict[str, Any]] = Field(default_factory=list)


class ClientPresence(AIpinhoModel):
    client_id: str
    surface: str
    last_seen_at: str = Field(default_factory=utc_now_iso)
    status: str = "online"
