from __future__ import annotations

from uuid import uuid4

from aipinho.schemas.patching.apply.patch_apply_event import PatchApplyEvent
from aipinho.services.session.session_store import utc_now


class PatchApplyEventService:
    def create(self, apply_run_id: str, event_type: str, summary: str, data: dict[str, object] | None = None) -> PatchApplyEvent:
        return PatchApplyEvent(
            event_id=f"patch_apply_event_{uuid4().hex}",
            apply_run_id=apply_run_id,
            event_type=event_type,
            created_at=utc_now(),
            summary=summary,
            data=data or {},
        )

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "patch_apply_event", "execution_enabled": False}
