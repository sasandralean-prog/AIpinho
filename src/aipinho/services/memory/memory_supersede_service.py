from __future__ import annotations

from aipinho.schemas.memory.curated_memory import CuratedMemoryRequest, MemorySupersedeRequest
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.memory.curated_memory_persistence_service import CuratedMemoryPersistenceService
from aipinho.services.memory.curated_memory_store import CuratedMemoryStore
from aipinho.services.memory.memory_candidate_service import MemoryCandidateService


class MemorySupersedeService:
    def __init__(
        self,
        store: CuratedMemoryStore | None = None,
        candidate_service: MemoryCandidateService | None = None,
        approval_service: ApprovalService | None = None,
    ) -> None:
        self.store = store or CuratedMemoryStore()
        self.candidate_service = candidate_service
        self.approval_service = approval_service

    def supersede(self, memory_id: str, request: MemorySupersedeRequest):
        if not request.reason:
            return None
        existing = self.store.get_memory(memory_id)
        if existing is None or existing.status != "active":
            return None
        return CuratedMemoryPersistenceService(store=self.store, candidate_service=self.candidate_service, approval_service=self.approval_service).persist(
            CuratedMemoryRequest(
                candidate_id=request.candidate_id,
                approval_id=request.approval_id,
                operator_confirmed=request.operator_confirmed,
                resolution="supersede_existing",
                supersede_memory_id=memory_id,
                reason=request.reason,
            )
        )
