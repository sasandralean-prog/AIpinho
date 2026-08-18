from __future__ import annotations

from aipinho.schemas.patching.quality.patch_quality_gate_result import PatchQualityGateResult


class PatchQualityAuditService:
    def audit(self, result: PatchQualityGateResult) -> dict[str, object]:
        return {
            "status": "ok",
            "quality_id": result.quality_id,
            "plan_id": result.plan_id,
            "decision": result.status,
            "apply_enabled": result.apply_enabled,
            "write_enabled": result.write_enabled,
            "findings": len(result.findings),
        }

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "patch_quality_audit", "execution_enabled": False}
