from __future__ import annotations

from aipinho.services.memory.curated_memory_store import CuratedMemoryStore


class CuratedMemoryEventService:
    def __init__(self, store: CuratedMemoryStore | None = None) -> None:
        self.store = store or CuratedMemoryStore()

    def append(self, memory_id: str, event_type: str, status: str, message: str, metadata: dict | None = None) -> None:
        self.store.append_event(memory_id, event_type, status, message, metadata or {})
