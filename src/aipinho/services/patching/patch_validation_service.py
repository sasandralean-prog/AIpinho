from __future__ import annotations

from aipinho.schemas.patching.diff_proposal import DiffProposal
from aipinho.schemas.patching.patch_evidence import PatchEvidence
from aipinho.schemas.patching.patch_risk import PatchRiskAssessment
from aipinho.schemas.patching.patch_validation import PatchValidationResult
from aipinho.schemas.patching.rollback_note import RollbackNote
from aipinho.schemas.patching.test_recommendation import TestRecommendation


class PatchValidationService:
    def validate(self, *, evidence: list[PatchEvidence], diff: DiffProposal | None, risk: PatchRiskAssessment, rollback_notes: list[RollbackNote], test_recommendations: list[TestRecommendation]) -> PatchValidationResult:
        blocked: list[str] = []
        evidence_valid = bool(evidence)
        diff_valid = bool(diff and diff.status == "generated" and diff.diff.diff_text)
        risk_valid = not risk.blocked and risk.risk_level != "critical"
        rollback_valid = bool(rollback_notes)
        tests_valid = bool(test_recommendations)
        if not evidence_valid:
            blocked.append("missing_evidence")
        if diff is None:
            blocked.append("missing_diff")
        elif not diff_valid:
            blocked.extend(diff.blocked_reasons or ["invalid_diff"])
        if not risk_valid:
            blocked.extend(risk.reasons or ["critical_risk"])
        if not rollback_valid:
            blocked.append("missing_rollback_notes")
        if not tests_valid:
            blocked.append("missing_test_recommendations")
        valid = not blocked and evidence_valid and risk_valid and rollback_valid and tests_valid
        status = "ready_for_review" if valid and not risk.needs_review else ("needs_review" if valid else "blocked")
        return PatchValidationResult(valid=valid, status=status, evidence_valid=evidence_valid, diff_valid=diff_valid, risk_valid=risk_valid, rollback_valid=rollback_valid, tests_recommended=tests_valid, blocked_reasons=list(dict.fromkeys(blocked)))

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "patch_validation", "apply_enabled": False, "write_enabled": False}
