from __future__ import annotations

from aipinho.schemas.patching.affected_file import AffectedFile
from aipinho.schemas.patching.patch_risk import PatchRiskAssessment


class PatchRiskService:
    def assess(self, files: list[AffectedFile], *, evidence_count: int, diff_chars: int = 0) -> PatchRiskAssessment:
        reasons: list[str] = []
        level = "low"
        if evidence_count <= 0:
            return PatchRiskAssessment(risk_level="critical", preview_allowed=False, blocked=True, reasons=["no_evidence"])
        if any(file.risk_level == "critical" or file.blocked_reasons for file in files):
            return PatchRiskAssessment(risk_level="critical", preview_allowed=False, blocked=True, reasons=["blocked_target"])
        if any(file.risk_level == "high" for file in files):
            level = "high"
            reasons.append("high_risk_target")
        elif len(files) > 1 or evidence_count == 1:
            level = "medium"
        if diff_chars > 30000:
            level = "high"
            reasons.append("large_diff")
        return PatchRiskAssessment(risk_level=level, preview_allowed=True, needs_review=level in {"medium", "high"}, blocked=False, reasons=reasons)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "patch_risk"}
