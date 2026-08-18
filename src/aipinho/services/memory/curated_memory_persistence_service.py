from __future__ import annotations

from uuid import uuid4

from aipinho.schemas.memory.curated_memory import (
    CuratedMemory,
    CuratedMemoryEvidence,
    CuratedMemoryRequest,
    CuratedMemoryResult,
    CuratedMemoryScope,
    CuratedMemorySource,
    CuratedMemoryTrace,
)
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.memory.curated_memory_store import CuratedMemoryStore
from aipinho.services.memory.curated_memory_version_service import CuratedMemoryVersionService
from aipinho.services.memory.memory_candidate_service import MemoryCandidateService
from aipinho.services.memory.memory_persistence_guard import MemoryPersistenceGuard
from aipinho.services.session.session_store import utc_now


class CuratedMemoryPersistenceService:
    def __init__(self, store: CuratedMemoryStore | None = None, candidate_service: MemoryCandidateService | None = None, approval_service: ApprovalService | None = None) -> None:
        self.store = store or CuratedMemoryStore()
        self.candidate_service = candidate_service or MemoryCandidateService()
        self.approval_service = approval_service or ApprovalService()
        self.guard = MemoryPersistenceGuard()
        self.versioning = CuratedMemoryVersionService()

    def persist(self, request: CuratedMemoryRequest) -> CuratedMemoryResult:
        candidate = self.candidate_service.get_candidate(request.candidate_id)
        approval = self.approval_service.get_approval(request.approval_id)
        guard = self.guard.validate(candidate=candidate, approval=approval, operator_confirmed=request.operator_confirmed, resolution=request.resolution, supersede_memory_id=request.supersede_memory_id)
        if not guard.allowed:
            return CuratedMemoryResult(status="blocked", blocked_reasons=guard.blocked_reasons, warnings=guard.warnings)
        if self._duplicates_active_memory(candidate) and request.resolution != "supersede_existing":
            return CuratedMemoryResult(status="blocked", blocked_reasons=["duplicate_curated_memory_blocks_new_memory"])
        now = utc_now()
        memory = CuratedMemory(
            memory_id=f"memory_{uuid4().hex}",
            status="active",
            kind=candidate.kind,
            summary=candidate.summary,
            text=candidate.text,
            source=CuratedMemorySource(**candidate.source.model_dump(), candidate_id=candidate.candidate_id, approval_id=request.approval_id),
            scope=CuratedMemoryScope(**candidate.scope.model_dump()),
            evidence=[CuratedMemoryEvidence(**item.model_dump()) for item in candidate.evidence],
            confidence=candidate.confidence,
            risk=candidate.risk,
            version=1,
            supersedes=request.supersede_memory_id if request.resolution == "supersede_existing" else None,
            warnings=list(candidate.warnings),
            trace=[*guard.trace, CuratedMemoryTrace(stage="persist", status="active", reason="curated_memory_persisted")],
            created_at=now,
            updated_at=now,
        )
        if memory.supersedes:
            old = self.store.get_memory(memory.supersedes)
            if old:
                old.status = "superseded"
                old.superseded_by = memory.memory_id
                old.updated_at = now
                self.store.save_memory(old)
                self.store.append_event(old.memory_id, "memory_superseded", "superseded", "Curated memory superseded by approved candidate.", {"superseded_by": memory.memory_id})
        self.store.save_memory(memory)
        self.store.save_versions(memory.memory_id, [self.versioning.initial_version(memory)])
        self.store.save_trace(memory.memory_id, memory.trace)
        self.store.append_event(memory.memory_id, "memory_persisted", "active", "Curated memory persisted after explicit approval.", {"candidate_id": candidate.candidate_id, "approval_id": request.approval_id})
        self.candidate_service.store.append_event(candidate.candidate_id, "candidate_persisted_as_curated_memory", candidate.status, "Candidate persisted as curated memory after explicit approval.", {"memory_id": memory.memory_id})
        return CuratedMemoryResult(status="active", memory=memory)

    def _duplicates_active_memory(self, candidate) -> bool:
        normalized = " ".join(candidate.text.lower().split())
        for memory in self.store.list_memories(status="active", kind=candidate.kind, scope=candidate.scope.scope_type, limit=10000):
            if " ".join(memory.text.lower().split()) == normalized:
                return True
        return False
