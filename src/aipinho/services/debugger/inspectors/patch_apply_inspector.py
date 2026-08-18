from __future__ import annotations

from aipinho.services.debugger.inspectors._shared import BaseInspector, finding
from aipinho.services.patching.apply.patch_apply_service import PatchApplyService


class PatchApplyInspector(BaseInspector):
    target_type = "patch_apply"

    def inspect(self, apply_run_id: str):
        service = PatchApplyService()
        run = service.get_run(apply_run_id)
        if run is None:
            return self.missing(apply_run_id)
        result = service.get_result(apply_run_id)
        data = {"run": run.model_dump(), "result": result.model_dump() if hasattr(result, "model_dump") else result}
        findings = []
        if not run.approval_id:
            findings.append(finding("patch_apply_missing_approval", "Patch apply run has no approval id"))
        if not run.quality_id:
            findings.append(finding("patch_apply_missing_quality_gate", "Patch apply run has no quality gate id"))
        if result is not None and not getattr(result, "safe_to_report_success", False):
            findings.append(finding("patch_apply_not_safe_to_report", "Patch apply result is not safe to report as success"))
        return self.result(apply_run_id, data, findings, summary="Patch apply inspected")
