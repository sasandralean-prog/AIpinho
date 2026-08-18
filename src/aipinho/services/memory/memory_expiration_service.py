from __future__ import annotations

from aipinho.services.memory.curated_memory_store import CuratedMemoryStore
from aipinho.services.session.session_store import utc_now


class MemoryExpirationService:
    def __init__(self, store: CuratedMemoryStore | None = None) -> None:
        self.store = store or CuratedMemoryStore()

    def expire(self, memory_id: str, reason: str):
        if not reason:
            return None
        memory = self.store.get_memory(memory_id)
        if memory is None or memory.status == "rejected":
            return None
        memory.status = "expired"
        memory.updated_at = utc_now()
        self.store.save_memory(memory)
        self.store.append_event(memory_id, "memory_expired", "expired", reason)
        return memory
