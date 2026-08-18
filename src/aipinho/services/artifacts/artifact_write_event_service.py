from __future__ import annotations

from uuid import uuid4

from aipinho.schemas.artifacts.artifact_write_event import ArtifactWriteEvent
from aipinho.services.session.session_store import utc_now


class ArtifactWriteEventService:
    def event(self, write_run_id: str, event_type: str, summary: str, *, status: str = "ok", data: dict[str, object] | None = None) -> ArtifactWriteEvent:
        return ArtifactWriteEvent(
            event_id=f"artifact_write_event_{uuid4().hex}",
            write_run_id=write_run_id,
            event_type=event_type,
            status=status,
            summary=summary,
            created_at=utc_now(),
            data=data or {},
        )

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "artifact_write_event", "orders_events": True}
