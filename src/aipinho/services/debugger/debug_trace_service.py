from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.schemas.debugger.debug_trace_event import DebugTraceEvent
from aipinho.services.debugger.debug_sanitizer import DebugSanitizer


class DebugTraceService:
    def __init__(self, store_dir: Path | None = None, sanitizer: DebugSanitizer | None = None) -> None:
        self.store_dir = store_dir or PATHS.project_root / "data" / "runtime" / "model_traces"
        self.sanitizer = sanitizer or DebugSanitizer()

    def create_trace(self, *, category: str = "debug", summary: str = "trace started") -> str:
        trace_id = f"trace_{uuid4().hex}"
        self.store_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "trace_id": trace_id,
            "category": category,
            "summary": summary,
            "created_at": self._now(),
            "events": [],
        }
        self._write(trace_id, payload)
        return trace_id

    def append_event(
        self,
        trace_id: str,
        *,
        event_type: str,
        status: str,
        summary: str,
        category: str = "debug",
        source: str | None = None,
        model_id: str | None = None,
        data: dict[str, object] | None = None,
    ) -> DebugTraceEvent:
        payload = self.get_trace(trace_id)
        event = DebugTraceEvent(
            event_id=f"event_{uuid4().hex}",
            trace_id=trace_id,
            event_type=event_type,
            status=status,
            summary=summary,
            category=category,
            source=source,
            sanitized=True,
            data=self.sanitizer.sanitize({"model_id": model_id, **(data or {})}),  # type: ignore[arg-type]
            created_at=self._now(),
        )
        events = payload.get("events", [])
        if not isinstance(events, list):
            events = []
        events.append(event.model_dump())
        payload["events"] = events
        payload["updated_at"] = self._now()
        self._write(trace_id, payload)
        return event

    def get_trace(self, trace_id: str) -> dict[str, object]:
        path = self._path(trace_id)
        if not path.exists():
            return {"trace_id": trace_id, "status": "missing", "events": []}
        return json.loads(path.read_text(encoding="utf-8"))

    def timeline(self, trace_id: str) -> dict[str, object]:
        trace = self.get_trace(trace_id)
        events = trace.get("events", [])
        items = []
        if isinstance(events, list):
            for event in events:
                if isinstance(event, dict):
                    items.append(
                        {
                            "trace_id": trace_id,
                            "event_id": event.get("event_id"),
                            "label": event.get("summary"),
                            "status": event.get("status"),
                            "category": event.get("category"),
                            "timestamp": event.get("created_at"),
                            "data": event.get("data", {}),
                        }
                    )
        return {"status": "ok" if trace.get("status") != "missing" else "missing", "trace_id": trace_id, "timeline": items}

    def _path(self, trace_id: str) -> Path:
        return self.store_dir / f"{trace_id}.json"

    def _write(self, trace_id: str, payload: dict[str, object]) -> None:
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self._path(trace_id).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
