from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from aipinho.core.paths import PATHS
from aipinho.services.session.session_store import utc_now
from aipinho.services.runtime.task_run_store import TaskRunStore

class TaskRunAuditService:
    def __init__(self, store: TaskRunStore | None = None, path: Path | None = None) -> None:
        self.store = store or TaskRunStore()
        self.path = path or self.store.root / "audit.jsonl"

    def record(self, *, run_id: str, action: str, status: str, reason: str = "", step_id: str | None = None, metadata: dict[str, Any] | None = None) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        item = self.store.sanitize({"timestamp": utc_now(), "run_id": run_id, "step_id": step_id, "action": action, "status": status, "reason": reason, "metadata": metadata or {}})
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "task_run_audit", "path": str(self.path), "raw_content_enabled": False}
