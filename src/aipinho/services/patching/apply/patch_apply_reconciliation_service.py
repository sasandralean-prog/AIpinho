from __future__ import annotations

from aipinho.schemas.patching.apply.patch_apply_reconciliation import PatchApplyReconciliation


class PatchApplyReconciliationService:
    def reconcile(self, expected_targets: list[str], observed_writes: list[str]) -> PatchApplyReconciliation:
        unexpected = sorted(set(observed_writes) - set(expected_targets))
        temp = [path for path in observed_writes if path.endswith(".aipinho_patch_tmp")]
        return PatchApplyReconciliation(status="ok" if not unexpected and not temp else "failed", expected_targets=expected_targets, observed_writes=observed_writes, unexpected_writes=unexpected, temp_files=temp)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "patch_apply_reconciliation"}
