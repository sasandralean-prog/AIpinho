from __future__ import annotations

from aipinho.schemas.memory.memory_candidate import MemoryCandidateTrace


class MemoryCandidateTraceService:
    def item(self, stage: str, status: str, reason: str, data: dict | None = None) -> MemoryCandidateTrace:
        return MemoryCandidateTrace(stage=stage, status=status, reason=reason, data=data or {})
