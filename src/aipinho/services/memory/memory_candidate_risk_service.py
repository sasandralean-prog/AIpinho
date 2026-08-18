from __future__ import annotations

from aipinho.schemas.memory.memory_candidate import MemoryCandidateRisk


class MemoryCandidateRiskService:
    def evaluate(self, *, source, scope, evidence, sensitivity, conflict, kind: str) -> MemoryCandidateRisk:
        reasons: list[str] = []
        level = "low"
        if sensitivity.status == "blocked":
            return MemoryCandidateRisk(level="critical", reasons=sensitivity.reasons, approval_future_required=True)
        if not source.source_type:
            reasons.append("no_source")
        if not scope.scope_type:
            reasons.append("no_scope")
        if kind != "user_instruction" and not evidence:
            reasons.append("no_evidence_for_technical_memory")
        if conflict.has_conflict:
            reasons.append("conflicts_existing_candidate")
        if any(reason in reasons for reason in {"no_source", "no_scope", "no_evidence_for_technical_memory"}):
            level = "critical"
        elif conflict.has_conflict:
            level = "high"
        elif kind in {"policy_decision", "architecture_decision", "project_constraint", "user_instruction"}:
            level = "medium"
        return MemoryCandidateRisk(level=level, reasons=list(dict.fromkeys(reasons)), approval_future_required=level in {"high", "critical"})
