from __future__ import annotations

import hashlib
from pathlib import Path

from aipinho.schemas.patching.affected_file import AffectedFile
from aipinho.schemas.patching.quality.patch_quality_finding import PatchQualityFinding
from aipinho.schemas.patching.quality.target_snapshot_validation import TargetSnapshotValidation


class TargetSnapshotValidator:
    def validate(self, affected_files: list[AffectedFile]) -> TargetSnapshotValidation:
        findings: list[PatchQualityFinding] = []
        checked = 0
        matched = 0
        mismatched = 0
        missing = 0
        for index, affected in enumerate(affected_files, start=1):
            if not affected.normalized_path:
                findings.append(PatchQualityFinding(finding_id=f"snapshot_missing_path_{index}", category="target_snapshot", severity="high", message="Arquivo afetado sem normalized_path auditavel.", file_path=affected.path, blocking=True))
                continue
            path = Path(affected.normalized_path)
            if not path.exists():
                missing += 1
                if affected.original_hash is None and "target_file_will_be_created" in affected.warnings:
                    checked += 1
                    matched += 1
                    continue
                findings.append(PatchQualityFinding(finding_id=f"snapshot_missing_file_{index}", category="target_snapshot", severity="critical", message="Arquivo alvo nao existe no snapshot atual.", file_path=affected.path, blocking=True))
                continue
            checked += 1
            if affected.original_hash:
                current_hash = hashlib.sha256(path.read_bytes()).hexdigest()
                if current_hash == affected.original_hash:
                    matched += 1
                else:
                    mismatched += 1
                    findings.append(PatchQualityFinding(finding_id=f"snapshot_hash_mismatch_{index}", category="target_snapshot", severity="critical", message="Hash atual difere do hash do preview; patch ficou stale.", file_path=affected.path, blocking=True))
        valid = not any(item.blocking for item in findings)
        return TargetSnapshotValidation(status="ok" if valid else "failed", valid=valid, checked_files=checked, matched_hashes=matched, mismatched_hashes=mismatched, missing_files=missing, findings=findings)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "target_snapshot_validator", "execution_enabled": False}
