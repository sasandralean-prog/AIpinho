from __future__ import annotations

from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.memory.curated_memory import CuratedMemoryRequest, MemoryExpirationRequest, MemorySearchRequest, MemorySupersedeRequest
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.memory.curated_memory_persistence_service import CuratedMemoryPersistenceService
from aipinho.services.memory.curated_memory_search_service import CuratedMemorySearchService
from aipinho.services.memory.curated_memory_store import CuratedMemoryStore
from aipinho.services.memory.memory_candidate_service import MemoryCandidateService
from aipinho.services.memory.memory_expiration_service import MemoryExpirationService
from aipinho.services.memory.memory_supersede_service import MemorySupersedeService
from aipinho.utils.yaml_loader import inspect_yaml_file


class CuratedMemoryService:
    CONFIGS = [
        "curated_memory_policy.yaml",
        "memory_approval_policy.yaml",
        "memory_persistence_policy.yaml",
        "curated_memory_store_policy.yaml",
        "curated_memory_validation_policy.yaml",
        "curated_memory_scope_policy.yaml",
        "curated_memory_evidence_policy.yaml",
        "curated_memory_versioning_policy.yaml",
        "curated_memory_dedupe_policy.yaml",
        "curated_memory_conflict_policy.yaml",
        "curated_memory_search_policy.yaml",
        "curated_memory_read_policy.yaml",
        "curated_memory_audit_policy.yaml",
        "curated_memory_lifecycle_policy.yaml",
    ]

    def __init__(
        self,
        store: CuratedMemoryStore | None = None,
        candidate_service: MemoryCandidateService | None = None,
        approval_service: ApprovalService | None = None,
    ) -> None:
        self.store = store or CuratedMemoryStore()
        self.candidate_service = candidate_service or MemoryCandidateService()
        self.approval_service = approval_service or ApprovalService()

    def persist_from_candidate(self, request: CuratedMemoryRequest):
        return CuratedMemoryPersistenceService(
            store=self.store,
            candidate_service=self.candidate_service,
            approval_service=self.approval_service,
        ).persist(request)

    def get_memory(self, memory_id: str):
        return self.store.get_memory(memory_id)

    def list_memories(self, **filters: Any):
        return self.store.list_memories(**filters)

    def search(self, request: MemorySearchRequest):
        return CuratedMemorySearchService(store=self.store).search(request)

    def supersede(self, memory_id: str, request: MemorySupersedeRequest):
        return MemorySupersedeService(store=self.store, candidate_service=self.candidate_service, approval_service=self.approval_service).supersede(memory_id, request)

    def expire(self, memory_id: str, request: MemoryExpirationRequest):
        return MemoryExpirationService(store=self.store).expire(memory_id, request.reason)

    def reject(self, memory_id: str, reason: str = "rejected") :
        memory = self.store.get_memory(memory_id)
        if memory is None:
            return None
        memory.status = "rejected"
        memory.updated_at = __import__("aipinho.services.session.session_store", fromlist=["utc_now"]).utc_now()
        self.store.save_memory(memory)
        self.store.append_event(memory_id, "memory_rejected", "rejected", reason)
        return memory

    def status(self) -> dict[str, Any]:
        root = PATHS.config_root / "memory"
        configs = {name: inspect_yaml_file(root / name, root=PATHS.project_root).__dict__ for name in self.CONFIGS}
        warnings = [f"{name}:{value.get('status')}" for name, value in configs.items() if value.get("status") != "ok"]
        return {
            "status": "degraded" if warnings else "ok",
            "service": "curated_memory",
            "curated_memory_enabled": True,
            "approved_memory_enabled": True,
            "approval_required": True,
            "candidate_required": True,
            "vectorstore_enabled": False,
            "embeddings_enabled": False,
            "rag_enabled": False,
            "auto_prompt_memory_enabled": False,
            "auto_chat_memory_enabled": False,
            "store": self.store.status(),
            "configs": configs,
            "warnings": warnings,
        }
