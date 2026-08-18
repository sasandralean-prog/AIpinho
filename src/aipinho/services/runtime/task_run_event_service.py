from __future__ import annotations
from uuid import uuid4
from aipinho.core.paths import PATHS
from aipinho.schemas.runtime.task_run_event import TaskRunEvent
from aipinho.services.runtime.task_run_store import TaskRunStore
from aipinho.utils.yaml_loader import load_yaml_file

class TaskRunEventService:
    def __init__(self, store: TaskRunStore | None = None) -> None:
        self.store = store or TaskRunStore()
        self.policy = load_yaml_file(PATHS.config_root / "runtime" / "task_run_event_policy.yaml", critical=True, root=PATHS.config_root / "runtime")

    def create(self, run_id: str, event_type: str, status: str, message: str, *, step_id: str | None = None, metadata: dict | None = None) -> TaskRunEvent:
        allowed = set(self.policy.get("events", {}).get("allowed_types", []) or [])
        if event_type not in allowed: raise ValueError(f"unknown_task_run_event:{event_type}")
        sequence = len(self.store.get_events(run_id)) + 1
        safe_meta = self.store.sanitize(metadata or {})
        event = TaskRunEvent(event_id=f"task_run_event_{uuid4().hex}", run_id=run_id, sequence=sequence, type=event_type, status=status, message=message[:1000], step_id=step_id, metadata=safe_meta)
        return self.store.append_event(run_id, event)

    def list(self, run_id: str) -> list[TaskRunEvent]:
        return sorted(self.store.get_events(run_id), key=lambda item: item.sequence)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "task_run_events", "raw_content_enabled": False}
