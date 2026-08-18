from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.chat.session_event import SessionEvent
from aipinho.schemas.chat.session_state import SessionState
from aipinho.utils.safe_paths import resolve_within_root


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dump_model(model) -> dict:
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()


def _parse_state(data: dict) -> SessionState:
    if hasattr(SessionState, "model_validate"):
        return SessionState.model_validate(data)
    return SessionState.parse_obj(data)


def _parse_event(data: dict) -> SessionEvent:
    if hasattr(SessionEvent, "model_validate"):
        return SessionEvent.model_validate(data)
    return SessionEvent.parse_obj(data)


class SessionStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or PATHS.project_root / "data" / "runtime" / "sessions"
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, session_id: str) -> Path:
        safe = resolve_within_root(self.root / f"{session_id}.json", self.root)
        return safe

    def _events_path(self, session_id: str) -> Path:
        safe = resolve_within_root(self.root / f"{session_id}.events.json", self.root)
        return safe

    def save(self, state: SessionState) -> SessionState:
        path = self._path(state.session_id)
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(_dump_model(state), ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(path)
        return state

    def get(self, session_id: str) -> SessionState | None:
        path = self._path(session_id)
        if not path.exists():
            return None
        return _parse_state(json.loads(path.read_text(encoding="utf-8")))

    def delete(self, session_id: str) -> bool:
        deleted = False
        for path in (self._path(session_id), self._events_path(session_id)):
            if path.exists():
                path.unlink()
                deleted = True
        return deleted

    def append_event(self, event: SessionEvent) -> None:
        events = self.list_events(event.session_id)
        events.append(event)
        path = self._events_path(event.session_id)
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps([_dump_model(item) for item in events], ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(path)

    def list_events(self, session_id: str) -> list[SessionEvent]:
        path = self._events_path(session_id)
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return []
        return [_parse_event(item) for item in data if isinstance(item, dict)]

    def status(self) -> dict[str, object]:
        return {"status": "ok", "store": "local_json", "path": str(self.root)}