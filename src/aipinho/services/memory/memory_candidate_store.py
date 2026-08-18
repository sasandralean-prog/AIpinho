from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.memory.memory_candidate import MemoryCandidate, MemoryCandidateEvent, MemoryCandidateTrace
from aipinho.services.session.session_store import utc_now
from aipinho.utils.safe_paths import resolve_within_root


def _dump(model: Any) -> dict[str, Any]:
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()


def _parse_candidate(data: dict[str, Any]) -> MemoryCandidate:
    if hasattr(MemoryCandidate, "model_validate"):
        return MemoryCandidate.model_validate(data)
    return MemoryCandidate.parse_obj(data)


class MemoryCandidateStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or PATHS.project_root / "data" / "runtime" / "memory_candidates"
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, candidate_id: str) -> Path:
        return resolve_within_root(self.root / f"{candidate_id}.json", self.root)

    def _events_path(self, candidate_id: str) -> Path:
        return resolve_within_root(self.root / f"{candidate_id}.events.json", self.root)

    def _trace_path(self, candidate_id: str) -> Path:
        return resolve_within_root(self.root / f"{candidate_id}.trace.json", self.root)

    def save_candidate(self, candidate: MemoryCandidate) -> MemoryCandidate:
        payload = self._sanitize(_dump(candidate))
        path = self._path(candidate.candidate_id)
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(path)
        return candidate

    def get_candidate(self, candidate_id: str) -> MemoryCandidate | None:
        path = self._path(candidate_id)
        if not path.exists():
            return None
        return _parse_candidate(json.loads(path.read_text(encoding="utf-8")))

    def list_candidates(self, *, status: str | None = None, kind: str | None = None, scope: str | None = None, source_type: str | None = None, risk_level: str | None = None, confidence: str | None = None, limit: int = 100) -> list[MemoryCandidate]:
        candidates: list[MemoryCandidate] = []
        for path in sorted(self.root.glob("memcand_*.json"), reverse=True):
            if path.name.endswith(".events.json") or path.name.endswith(".trace.json"):
                continue
            candidate = _parse_candidate(json.loads(path.read_text(encoding="utf-8")))
            if status and candidate.status != status:
                continue
            if kind and candidate.kind != kind:
                continue
            if scope and candidate.scope.scope_type != scope:
                continue
            if source_type and candidate.source.source_type != source_type:
                continue
            if risk_level and candidate.risk.level != risk_level:
                continue
            if confidence and candidate.confidence != confidence:
                continue
            candidates.append(candidate)
            if len(candidates) >= limit:
                break
        return candidates

    def update_candidate_status(self, candidate_id: str, status: str, reason: str) -> MemoryCandidate | None:
        candidate = self.get_candidate(candidate_id)
        if candidate is None:
            return None
        if status == "approved":
            status = "blocked"
            reason = "approved_state_forbidden_this_sprint"
        candidate.status = status  # type: ignore[assignment]
        candidate.updated_at = utc_now()
        candidate.warnings = list(dict.fromkeys([*candidate.warnings, reason]))
        self.save_candidate(candidate)
        return candidate

    def append_event(self, candidate_id: str, event_type: str, status: str, message: str, metadata: dict[str, Any] | None = None) -> None:
        events = self.get_events(candidate_id)
        event = MemoryCandidateEvent(event_id=f"memcand_evt_{len(events)+1}", candidate_id=candidate_id, event_type=event_type, status=status, message=message, created_at=utc_now(), metadata=metadata or {})
        events.append(event)
        path = self._events_path(candidate_id)
        path.write_text(json.dumps([_dump(item) for item in events], ensure_ascii=False, indent=2), encoding="utf-8")

    def get_events(self, candidate_id: str) -> list[MemoryCandidateEvent]:
        path = self._events_path(candidate_id)
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        return [MemoryCandidateEvent.model_validate(item) if hasattr(MemoryCandidateEvent, "model_validate") else MemoryCandidateEvent.parse_obj(item) for item in data]

    def save_trace(self, candidate_id: str, trace: list[MemoryCandidateTrace]) -> None:
        self._trace_path(candidate_id).write_text(json.dumps([_dump(item) for item in trace], ensure_ascii=False, indent=2), encoding="utf-8")

    def get_trace(self, candidate_id: str) -> list[dict[str, Any]]:
        path = self._trace_path(candidate_id)
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    def status(self) -> dict[str, Any]:
        return {"status": "ok", "store": "local_json", "path": str(self.root), "candidate_count": len(list(self.root.glob("memcand_*.json")))}

    def _sanitize(self, payload: Any) -> Any:
        if isinstance(payload, dict):
            return {key: self._sanitize(value) for key, value in payload.items()}
        if isinstance(payload, list):
            return [self._sanitize(item) for item in payload]
        if isinstance(payload, str):
            import re

            redacted = re.sub(r"(?i)(api[_-]?key|token|password|passwd|secret)\s*[:=]\s*['\"]?([A-Za-z0-9_\-]{6,})", r"\1=[REDACTED]", payload)
            redacted = re.sub(r"sk-[A-Za-z0-9]{12,}", "sk-[REDACTED]", redacted)
            return redacted
        return payload
