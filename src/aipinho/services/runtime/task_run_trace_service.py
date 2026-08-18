from __future__ import annotations
from typing import Any
from aipinho.schemas.runtime.task_run_trace import TaskRunTraceItem

class TaskRunTraceService:
    def item(self, stage: str, status: str, reason: str = "", *, step_id: str | None = None, source: str | None = None, data: dict[str, Any] | None = None) -> TaskRunTraceItem:
        return TaskRunTraceItem(stage=stage, status=status, reason=reason, step_id=step_id, source=source, data=data or {})

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "task_run_trace", "raw_content_enabled": False}
