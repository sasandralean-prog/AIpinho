from __future__ import annotations

from aipinho.schemas.patching.quality.patch_quality_finding import PatchQualityFinding
from aipinho.schemas.patching.quality.patch_quality_score import PatchQualityScore


class PatchQualityScoreService:
    def score(self, findings: list[PatchQualityFinding]) -> PatchQualityScore:
        blocking = [item for item in findings if item.blocking]
        critical = [item for item in findings if item.severity == "critical"]
        warnings = [item for item in findings if not item.blocking]
        penalty = len(blocking) * 25 + len(critical) * 20 + len(warnings) * 5
        score = max(0.0, 100.0 - float(penalty))
        if critical:
            status = "rejected"
            reason = "critical_quality_findings"
        elif blocking:
            status = "failed"
            reason = "blocking_quality_findings"
        elif warnings:
            status = "needs_review"
            reason = "non_blocking_quality_findings"
        else:
            status = "passed"
            reason = "no_quality_findings"
        return PatchQualityScore(
            status=status,
            score=score,
            blocking_findings=len(blocking),
            warning_count=len(warnings),
            critical_count=len(critical),
            decision_reason=reason,
            dimensions={
                "blocking": float(len(blocking)),
                "critical": float(len(critical)),
                "warning": float(len(warnings)),
            },
        )

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "patch_quality_score", "execution_enabled": False}
