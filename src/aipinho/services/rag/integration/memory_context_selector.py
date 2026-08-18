from __future__ import annotations

import hashlib

from aipinho.schemas.rag.integration.contracts import ContextInjectionItem, MemoryContextSelection
from aipinho.services.memory.curated_memory_search_service import CuratedMemorySearchService
from aipinho.services.memory.memory_read_policy_service import MemoryReadPolicyService
from aipinho.services.rag.integration.context_provenance_service import ContextProvenanceService


class MemoryContextSelector:
    def __init__(
        self,
        search: CuratedMemorySearchService | None = None,
        read_policy: MemoryReadPolicyService | None = None,
        provenance: ContextProvenanceService | None = None,
    ) -> None:
        self.search = search or CuratedMemorySearchService()
        self.read_policy = read_policy or MemoryReadPolicyService()
        self.provenance = provenance or ContextProvenanceService()

    def select(self, memories: list[dict], *, explicit: bool, workspace: str | None = None, max_items: int = 4) -> MemoryContextSelection:
        if not explicit or not self.read_policy.explicit_read_allowed():
            return MemoryContextSelection(blocked_reasons=["curated_memory_explicit_required"])
        items: list[ContextInjectionItem] = []
        blocked_items: list[dict] = []
        for memory in memories:
            memory_id = str(memory.get("memory_id") or "")
            status = str(memory.get("status") or "")
            evidence = memory.get("evidence") or []
            scope = memory.get("scope") or {}
            if status != "active":
                blocked_items.append({"memory_id": memory_id, "reason": f"memory_status_blocked:{status or 'missing'}"})
                continue
            if not evidence:
                blocked_items.append({"memory_id": memory_id, "reason": "memory_evidence_required"})
                continue
            if workspace and scope.get("workspace") and scope.get("workspace") != workspace:
                blocked_items.append({"memory_id": memory_id, "reason": "memory_scope_mismatch"})
                continue
            content = str(memory.get("summary") or memory.get("text") or "")
            citation_id = "citation_memory_" + hashlib.sha256(f"{memory_id}:{memory.get('version')}".encode("utf-8")).hexdigest()[:24]
            provenance = self.provenance.from_memory(memory=memory, citation_id=citation_id, origin_reason="memory_explicit_read")
            items.append(
                ContextInjectionItem(
                    kind="curated_memory",
                    source_type="curated_memory",
                    source_id="curated_memory",
                    content=content,
                    citation_ids=[citation_id],
                    provenance=provenance,
                    score=0.5,
                    rank=len(items) + 1,
                    metadata={
                        "memory_id": memory_id,
                        "memory_status": status,
                        "memory_version": memory.get("version"),
                        "created_at": memory.get("created_at"),
                        "scope": scope,
                        "evidence_ids": [item.get("evidence_id") for item in evidence if isinstance(item, dict)],
                    },
                )
            )
            if len(items) >= max_items:
                break
        reasons = ["memory_items_blocked"] if blocked_items and not items else []
        return MemoryContextSelection(items=items, blocked_items=blocked_items, blocked_reasons=reasons)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "memory_context_selector", "active_only": True, "explicit_required": True}
