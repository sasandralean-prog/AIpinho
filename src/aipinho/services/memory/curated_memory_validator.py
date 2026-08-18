from __future__ import annotations

from aipinho.schemas.memory.curated_memory import MemoryPersistenceValidation
from aipinho.services.memory.memory_candidate_evidence_service import MemoryCandidateEvidenceService
from aipinho.services.memory.memory_candidate_scope_service import MemoryCandidateScopeService
from aipinho.services.memory.memory_candidate_sensitivity_scanner import MemoryCandidateSensitivityScanner


class CuratedMemoryValidator:
    def validate_candidate(self, candidate) -> MemoryPersistenceValidation:
        reasons: list[str] = []
        warnings: list[str] = []
        if candidate is None:
            reasons.append("candidate_not_found")
            return MemoryPersistenceValidation(allowed=False, status="blocked", blocked_reasons=reasons)
        if candidate.status not in {"candidate", "needs_review"}:
            reasons.append(f"candidate_status_blocked:{candidate.status}")
        if not candidate.source.source_type or not (candidate.source.source_id or candidate.source.source_ref):
            reasons.append("source_missing")
        reasons.extend(MemoryCandidateScopeService().validate(candidate.scope))
        reasons.extend(MemoryCandidateEvidenceService().validate(candidate.evidence, kind=candidate.kind))
        scan = MemoryCandidateSensitivityScanner().scan(candidate.text, evidence=candidate.evidence)
        if scan.status != "safe":
            reasons.extend(scan.reasons)
        if candidate.dedupe.status == "duplicate":
            reasons.append("duplicate_candidate_blocked")
        if candidate.conflict.has_conflict:
            reasons.append("unresolved_candidate_conflict")
        if candidate.risk.level == "critical":
            reasons.extend(candidate.risk.reasons)
        return MemoryPersistenceValidation(allowed=not reasons, status="allowed" if not reasons else "blocked", blocked_reasons=list(dict.fromkeys(reasons)), warnings=warnings)
