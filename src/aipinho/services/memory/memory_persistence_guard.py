from __future__ import annotations

from aipinho.schemas.memory.curated_memory import CuratedMemoryTrace, MemoryPersistenceValidation
from aipinho.services.memory.curated_memory_validator import CuratedMemoryValidator


class MemoryPersistenceGuard:
    def validate(self, *, candidate, approval, operator_confirmed: bool, resolution: str | None = None, supersede_memory_id: str | None = None) -> MemoryPersistenceValidation:
        reasons: list[str] = []
        warnings: list[str] = []
        trace = [CuratedMemoryTrace(stage="guard", status="checking", reason="memory_persistence_guard")]
        candidate_check = CuratedMemoryValidator().validate_candidate(candidate)
        reasons.extend(candidate_check.blocked_reasons)
        warnings.extend(candidate_check.warnings)
        if candidate and candidate.conflict.has_conflict and resolution == "supersede_existing" and supersede_memory_id:
            reasons = [reason for reason in reasons if reason != "unresolved_candidate_conflict"]
        if candidate and candidate.dedupe.status == "near_duplicate" and resolution in {"supersede_existing", "link_to_existing"}:
            reasons = [reason for reason in reasons if reason != "duplicate_candidate_blocked"]
        if approval is None:
            reasons.append("approval_missing")
        else:
            if approval.status != "approved":
                reasons.append(f"approval_not_approved:{approval.status}")
            if approval.approval_scope != "curated_memory_persist":
                reasons.append(f"approval_scope_mismatch:{approval.approval_scope}")
            meta = approval.policy_snapshot.config_versions.get("memory", {}) if approval.policy_snapshot else {}
            if candidate and meta.get("candidate_id") != candidate.candidate_id:
                reasons.append("approval_candidate_mismatch")
            if candidate and meta.get("kind") != candidate.kind:
                reasons.append("approval_kind_mismatch")
        if not operator_confirmed:
            reasons.append("operator_confirmation_required")
        # These are fixed false by policy in Sprint 24.
        vectorstore_enabled = False
        embeddings_enabled = False
        rag_enabled = False
        if vectorstore_enabled or embeddings_enabled or rag_enabled:
            reasons.append("forbidden_memory_backend_enabled")
        status = "allowed" if not reasons else "blocked"
        trace.append(CuratedMemoryTrace(stage="guard", status=status, reason=";".join(reasons) or "allowed"))
        return MemoryPersistenceValidation(allowed=not reasons, status=status, blocked_reasons=list(dict.fromkeys(reasons)), warnings=list(dict.fromkeys(warnings)), trace=trace)
