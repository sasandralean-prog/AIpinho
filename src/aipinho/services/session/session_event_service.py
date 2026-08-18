from __future__ import annotations

from uuid import uuid4

from aipinho.schemas.chat.session_event import SessionEvent, SessionEventType
from aipinho.services.session.session_store import utc_now


class SessionEventService:
    def create(self, *, session_id: str, event_type: SessionEventType, summary: str, data: dict | None = None, warnings: list[str] | None = None) -> SessionEvent:
        return SessionEvent(
            event_id=f"session_event_{uuid4().hex}",
            session_id=session_id,
            event_type=event_type,
            created_at=utc_now(),
            summary=summary,
            data=data or {},
            warnings=warnings or [],
        )