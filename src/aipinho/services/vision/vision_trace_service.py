from __future__ import annotations

import json
from uuid import uuid4

from aipinho.services.vision.config import runtime_path


class VisionTraceService:
    def __init__(self) -> None:
        self.root = runtime_path("traces")

    def create(self, summary: str) -> str:
        trace_id = f"vision_trace_{uuid4().hex}"
        self._write(trace_id, [{"event_type": "trace_created", "status": "ok", "summary": summary, "data": {}}])
        return trace_id

    def record(self, trace_id: str, *, event_type: str, status: str, summary: str, data: dict | None = None) -> None:
        events = self.get(trace_id).get("events", [])
        events.append({"event_type": event_type, "status": status, "summary": summary, "data": data or {}})
        self._write(trace_id, events)

    def get(self, trace_id: str) -> dict:
        path = self.root / f"{trace_id}.json"
        if not path.exists():
            return {"trace_id": trace_id, "events": []}
        return json.loads(path.read_text(encoding="utf-8"))

    def _write(self, trace_id: str, events: list[dict]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / f"{trace_id}.json").write_text(json.dumps({"trace_id": trace_id, "events": events}, indent=2, ensure_ascii=False), encoding="utf-8")

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "vision_trace", "root": str(self.root)}
