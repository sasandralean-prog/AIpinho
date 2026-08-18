from __future__ import annotations

from aipinho.schemas.memory.memory_candidate import MemoryCandidateValidation
from aipinho.services.memory.memory_candidate_evidence_service import MemoryCandidateEvidenceService
from aipinho.services.memory.memory_candidate_scope_service import MemoryCandidateScopeService


class MemoryCandidateValidator:
    def validate(self, *, text: str, requested_status: str, kind: str, source, scope, evidence, sensitivity, dedupe, conflict, risk) -> MemoryCandidateValidation:
        reasons: list[str] = []
        warnings: list[str] = []
        if requested_status == "approved":
            reasons.append("approved_state_forbidden_this_sprint")
        if not text.strip():
            reasons.append("empty_text")
        if not kind:
            reasons.append("kind_missing")
        if not source.source_type:
            reasons.append("source_missing")
        if not (source.source_id or source.source_payload or source.source_ref):
            reasons.append("source_id_or_payload_missing")
        reasons.extend(MemoryCandidateScopeService().validate(scope))
        reasons.extend(MemoryCandidateEvidenceService().validate(evidence, kind=kind))
        if sensitivity.status == "blocked":
            reasons.extend(sensitivity.reasons)
        if dedupe.status == "near_duplicate":
            warnings.append("near_duplicate_needs_review")
        if conflict.has_conflict:
            warnings.extend(conflict.reasons)
        if risk.level == "critical":
            reasons.extend(risk.reasons)
        reasons = list(dict.fromkeys(reasons))
        return MemoryCandidateValidation(status="passed" if not reasons else "blocked", passed=not reasons, reasons=reasons, warnings=list(dict.fromkeys(warnings)))
