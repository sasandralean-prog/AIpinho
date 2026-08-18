from __future__ import annotations

from aipinho.schemas.patching.patch_plan import PatchPlan
from aipinho.schemas.patching.quality.patch_quality_finding import PatchQualityFinding


class EvidenceLinkValidator:
    def validate(self, plan: PatchPlan | None) -> list[PatchQualityFinding]:
        if plan is None:
            return []
        evidence_ids = {item.evidence_id for item in plan.evidence}
        findings: list[PatchQualityFinding] = []
        for index, hunk in enumerate(plan.hunks, start=1):
            if not hunk.evidence_ids:
                findings.append(PatchQualityFinding(finding_id=f"evidence_missing_{index}", category="evidence", severity="high", message="Hunk sem evidencia vinculada.", file_path=hunk.file_path, blocking=True))
                continue
            missing = [item for item in hunk.evidence_ids if item not in evidence_ids]
            if missing:
                findings.append(PatchQualityFinding(finding_id=f"evidence_unknown_{index}", category="evidence", severity="high", message="Hunk referencia evidencia inexistente.", file_path=hunk.file_path, blocking=True, metadata={"missing": missing}))
        return findings

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "evidence_link_validator", "execution_enabled": False}
