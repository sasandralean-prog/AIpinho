from __future__ import annotations

from aipinho.schemas.memory.curated_memory import CuratedMemoryAudit
from aipinho.services.session.session_store import utc_now


class CuratedMemoryAuditService:
    def audit(self, memory_id: str, event_type: str, *, candidate_id: str | None = None, approval_id: str | None = None) -> CuratedMemoryAudit:
        return CuratedMemoryAudit(memory_id=memory_id, event_type=event_type, created_at=utc_now(), candidate_id=candidate_id, approval_id=approval_id)
