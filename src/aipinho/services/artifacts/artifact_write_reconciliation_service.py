from __future__ import annotations

from pathlib import Path


class ArtifactWriteReconciliationService:
    def temp_exists(self, target_path: str, *, suffix: str = ".aipinho_tmp") -> bool:
        target = Path(target_path)
        return target.with_name(target.name + suffix).exists()

    def cleanup_temp(self, target_path: str, *, suffix: str = ".aipinho_tmp") -> bool:
        target = Path(target_path)
        temp = target.with_name(target.name + suffix)
        if temp.exists():
            temp.unlink()
            return True
        return False

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "artifact_write_reconciliation"}
