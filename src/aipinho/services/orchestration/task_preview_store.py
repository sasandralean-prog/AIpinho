from __future__ import annotations

import json
from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.tasks.task_preview import TaskPreview
from aipinho.schemas.tasks.task_preview_event import TaskPreviewEvent
from aipinho.utils.safe_paths import resolve_within_root


def _dump_model(model) -> dict:
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()


def _parse_preview(data: dict) -> TaskPreview:
    if hasattr(TaskPreview, "model_validate"):
        return TaskPreview.model_validate(data)
    return TaskPreview.parse_obj(data)


def _parse_event(data: dict) -> TaskPreviewEvent:
    if hasattr(TaskPreviewEvent, "model_validate"):
        return TaskPreviewEvent.model_validate(data)
    return TaskPreviewEvent.parse_obj(data)


class TaskPreviewStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or PATHS.project_root / "data" / "runtime" / "previews"
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, preview_id: str) -> Path:
        return resolve_within_root(self.root / f"{preview_id}.json", self.root)

    def _events_path(self, preview_id: str) -> Path:
        return resolve_within_root(self.root / f"{preview_id}.events.json", self.root)

    def save(self, preview: TaskPreview) -> TaskPreview:
        path = self._path(preview.preview_id)
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(_dump_model(preview), ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(path)
        return preview

    def get(self, preview_id: str) -> TaskPreview | None:
        path = self._path(preview_id)
        if not path.exists():
            return None
        return _parse_preview(json.loads(path.read_text(encoding="utf-8")))

    def append_event(self, event: TaskPreviewEvent) -> None:
        events = self.list_events(event.preview_id)
        events.append(event)
        path = self._events_path(event.preview_id)
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps([_dump_model(item) for item in events], ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(path)

    def list_events(self, preview_id: str) -> list[TaskPreviewEvent]:
        path = self._events_path(preview_id)
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return []
        return [_parse_event(item) for item in data if isinstance(item, dict)]

    def status(self) -> dict[str, object]:
        return {"status": "ok", "store": "local_json", "path": str(self.root)}