from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from aipinho.core.paths import PATHS


class RoleInferenceAuditService:
    def __init__(self, audit_path: Path | None = None) -> None:
        self.audit_path = audit_path or PATHS.project_root / "data" / "runtime" / "role_model_runs" / "audit.jsonl"

    def record(self, payload: dict[str, object]) -> None:
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(), **payload}, ensure_ascii=False)
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "role_inference_audit", "path": str(self.audit_path)}
