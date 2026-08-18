from __future__ import annotations

from aipinho.schemas.patching.quality.patch_quality_score import PatchQualityScore


class PatchQualityDecisionService:
    def decide(self, score: PatchQualityScore) -> tuple[str, bool]:
        if score.status == "passed":
            return "passed", True
        if score.status == "needs_review" and score.critical_count == 0 and score.blocking_findings == 0:
            return "passed_with_warnings", True
        if score.status == "failed":
            return "failed", False
        if score.status == "rejected":
            return "rejected", False
        return "needs_review", False

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "patch_quality_decision", "execution_enabled": False}
