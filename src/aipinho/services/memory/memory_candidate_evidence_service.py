from __future__ import annotations

from uuid import uuid4

from aipinho.schemas.memory.memory_candidate import MemoryCandidateEvidence, MemoryCandidateSource


class MemoryCandidateEvidenceService:
    TECHNICAL_KINDS = {
        "architecture_decision",
        "policy_decision",
        "validation_learning",
        "bug_fix_summary",
        "patch_outcome",
        "runtime_behavior",
        "project_constraint",
        "testing_guidance",
        "risk_pattern",
    }

    def build(self, evidence: list[MemoryCandidateEvidence], *, source: MemoryCandidateSource, text: str, kind: str) -> list[MemoryCandidateEvidence]:
        if evidence:
            return evidence
        if source.source_type == "user_instruction" and kind == "user_instruction":
            return [
                MemoryCandidateEvidence(
                    evidence_id=f"evidence_{uuid4().hex}",
                    evidence_type="user_explicit_instruction",
                    source_ref=source.source_ref or source.source_type,
                    summary=text[:300],
                )
            ]
        return []

    def validate(self, evidence: list[MemoryCandidateEvidence], *, kind: str) -> list[str]:
        reasons: list[str] = []
        if kind in self.TECHNICAL_KINDS and not evidence:
            reasons.append("evidence_missing_for_technical_memory")
        for item in evidence:
            if not item.evidence_id:
                reasons.append("evidence_id_missing")
            if not item.source_ref:
                reasons.append("evidence_source_ref_missing")
            if not item.summary:
                reasons.append("evidence_summary_missing")
        return reasons

    def confidence(self, *, evidence: list[MemoryCandidateEvidence], source: MemoryCandidateSource, kind: str) -> str:
        if len(evidence) >= 2 and source.trusted:
            return "high"
        if evidence:
            return "medium"
        return "low"
