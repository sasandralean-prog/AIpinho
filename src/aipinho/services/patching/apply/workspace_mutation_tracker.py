from __future__ import annotations

from pathlib import Path

from aipinho.schemas.patching.apply.patch_apply_reconciliation import PatchApplyReconciliation


class WorkspaceMutationTracker:
    def __init__(self, expected_targets: list[str]) -> None:
        self.expected_targets = [str(Path(path)) for path in expected_targets]
        self.observed_writes: list[str] = []

    def record_write(self, path: Path) -> None:
        self.observed_writes.append(str(path))

    def reconcile(self) -> PatchApplyReconciliation:
        expected = {str(Path(path)) for path in self.expected_targets}
        observed = {str(Path(path)) for path in self.observed_writes}
        unexpected = sorted(observed - expected)
        temp_files = [path for path in observed if path.endswith(".aipinho_patch_tmp")]
        return PatchApplyReconciliation(status="ok" if not unexpected and not temp_files else "failed", expected_targets=sorted(expected), observed_writes=sorted(observed), unexpected_writes=unexpected, temp_files=temp_files)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "workspace_mutation_tracker"}
