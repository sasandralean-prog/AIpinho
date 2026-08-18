from __future__ import annotations

from aipinho.services.memory.memory_candidate_store import MemoryCandidateStore


class MemoryCandidateEventService:
    def __init__(self, store: MemoryCandidateStore | None = None) -> None:
        self.store = store or MemoryCandidateStore()

    def append(self, candidate_id: str, event_type: str, status: str, message: str, metadata: dict | None = None) -> None:
        self.store.append_event(candidate_id, event_type, status, message, metadata or {})
