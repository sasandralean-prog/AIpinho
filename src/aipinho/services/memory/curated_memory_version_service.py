from __future__ import annotations

import hashlib

from aipinho.schemas.memory.curated_memory import CuratedMemory, CuratedMemoryVersion


class CuratedMemoryVersionService:
    def initial_version(self, memory: CuratedMemory) -> CuratedMemoryVersion:
        return CuratedMemoryVersion(memory_id=memory.memory_id, version=1, status=memory.status, created_at=memory.created_at, candidate_id=memory.source.candidate_id, approval_id=memory.source.approval_id, summary_hash=self._hash(memory.summary), supersedes=memory.supersedes, reason="initial_version")

    def supersede_version(self, memory: CuratedMemory, *, reason: str) -> CuratedMemoryVersion:
        return CuratedMemoryVersion(memory_id=memory.memory_id, version=memory.version, status=memory.status, created_at=memory.created_at, candidate_id=memory.source.candidate_id, approval_id=memory.source.approval_id, summary_hash=self._hash(memory.summary), supersedes=memory.supersedes, reason=reason)

    def _hash(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
