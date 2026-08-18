from __future__ import annotations

from aipinho.schemas.memory.memory_candidate import MemoryCandidate, MemoryCandidateAudit
from aipinho.services.session.session_store import utc_now


class MemoryCandidateAuditService:
    def audit(self, candidate: MemoryCandidate) -> MemoryCandidateAudit:
        return MemoryCandidateAudit(candidate_id=candidate.candidate_id, created_at=utc_now(), source_type=candidate.source.source_type)
