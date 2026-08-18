from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.utils.safe_paths import resolve_within_root


class RolePipelineAuditService:
    def __init__(self, runs_dir: Path | None = None) -> None:
        self.runs_dir = runs_dir or PATHS.project_root / "data" / "runtime" / "role_pipeline_runs"

    def record(self, *, run_id: str, pipeline_id: str, pass_id: str | None, role_id: str | None, status: str, model_id: str | None = None, real_inference: bool = False, evaluation_status: str | None = None) -> dict[str, object]:
        event = {
            "audit_event_id": f"role_audit_{uuid4().hex}",
            "run_id": run_id,
            "pipeline_id": pipeline_id,
            "pass_id": pass_id,
            "role_id": role_id,
            "status": status,
            "model_id": model_id,
            "real_inference": real_inference,
            "evaluation_status": evaluation_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        path = resolve_within_root(self.runs_dir / "audit.jsonl", PATHS.project_root)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        return event

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "role_pipeline_audit", "persist_full_prompt": False, "persist_full_output": False}
