from __future__ import annotations

from aipinho.schemas.memory.curated_memory import CuratedMemoryTrace


class CuratedMemoryTraceService:
    def item(self, stage: str, status: str, reason: str, data: dict | None = None) -> CuratedMemoryTrace:
        return CuratedMemoryTrace(stage=stage, status=status, reason=reason, data=data or {})
