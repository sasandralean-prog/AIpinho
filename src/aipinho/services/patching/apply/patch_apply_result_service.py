from __future__ import annotations

from aipinho.schemas.patching.apply.patch_apply_result import PatchApplyResult


class PatchApplyResultService:
    def is_success(self, result: PatchApplyResult) -> bool:
        return result.status == "completed" and result.post_apply_validation.passed is True and result.safe_to_report_success is True

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "patch_apply_result"}
