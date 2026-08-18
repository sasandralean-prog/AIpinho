from __future__ import annotations

from aipinho.schemas.patching.apply.patch_apply_result import PatchApplyResult
from aipinho.schemas.patching.apply.patch_apply_run import PatchApplyRun


class PatchApplyAuditService:
    def audit(self, run: PatchApplyRun, result: PatchApplyResult | None = None) -> dict[str, object]:
        return {
            "status": "ok",
            "apply_run_id": run.apply_run_id,
            "plan_id": run.plan_id,
            "run_status": run.status,
            "result_status": result.status if result else None,
            "backup_ids": list(run.backup_ids),
            "shell_enabled": False,
            "git_enabled": False,
        }

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "patch_apply_audit"}
