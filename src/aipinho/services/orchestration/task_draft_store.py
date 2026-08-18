from __future__ import annotations

import json
from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.tasks.task_contract_draft import TaskContractDraft
from aipinho.schemas.tasks.task_draft_event import TaskDraftEvent
from aipinho.utils.safe_paths import resolve_within_root


def _dump_model(model) -> dict:
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()


def _parse_draft(data: dict) -> TaskContractDraft:
    if hasattr(TaskContractDraft, "model_validate"):
        return TaskContractDraft.model_validate(data)
    return TaskContractDraft.parse_obj(data)


def _parse_event(data: dict) -> TaskDraftEvent:
    if hasattr(TaskDraftEvent, "model_validate"):
        return TaskDraftEvent.model_validate(data)
    return TaskDraftEvent.parse_obj(data)


class TaskDraftStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or PATHS.project_root / "data" / "runtime" / "task_drafts"
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, draft_id: str) -> Path:
        return resolve_within_root(self.root / f"{draft_id}.json", self.root)

    def _events_path(self, draft_id: str) -> Path:
        return resolve_within_root(self.root / f"{draft_id}.events.json", self.root)

    def save(self, draft: TaskContractDraft) -> TaskContractDraft:
        path = self._path(draft.draft_id)
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(_dump_model(draft), ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(path)
        return draft

    def get(self, draft_id: str) -> TaskContractDraft | None:
        path = self._path(draft_id)
        if not path.exists():
            return None
        return _parse_draft(json.loads(path.read_text(encoding="utf-8")))

    def delete(self, draft_id: str) -> bool:
        deleted = False
        for path in (self._path(draft_id), self._events_path(draft_id)):
            if path.exists():
                path.unlink()
                deleted = True
        return deleted

    def append_event(self, event: TaskDraftEvent) -> None:
        events = self.list_events(event.draft_id)
        events.append(event)
        path = self._events_path(event.draft_id)
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps([_dump_model(item) for item in events], ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(path)

    def list_events(self, draft_id: str) -> list[TaskDraftEvent]:
        path = self._events_path(draft_id)
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return []
        return [_parse_event(item) for item in data if isinstance(item, dict)]

    def status(self) -> dict[str, object]:
        return {"status": "ok", "store": "local_json", "path": str(self.root)}