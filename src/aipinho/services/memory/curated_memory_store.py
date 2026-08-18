from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.memory.curated_memory import CuratedMemory, CuratedMemoryEvent, CuratedMemoryTrace, CuratedMemoryVersion
from aipinho.services.session.session_store import utc_now
from aipinho.utils.safe_paths import resolve_within_root


def _dump(model: Any) -> dict[str, Any]:
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()


def _parse_memory(data: dict[str, Any]) -> CuratedMemory:
    if hasattr(CuratedMemory, "model_validate"):
        return CuratedMemory.model_validate(data)
    return CuratedMemory.parse_obj(data)


class CuratedMemoryStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or PATHS.project_root / "data" / "memory" / "curated"
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, memory_id: str) -> Path:
        return resolve_within_root(self.root / f"{memory_id}.json", self.root)

    def _events_path(self, memory_id: str) -> Path:
        return resolve_within_root(self.root / f"{memory_id}.events.json", self.root)

    def _trace_path(self, memory_id: str) -> Path:
        return resolve_within_root(self.root / f"{memory_id}.trace.json", self.root)

    def _versions_path(self, memory_id: str) -> Path:
        return resolve_within_root(self.root / f"{memory_id}.versions.json", self.root)

    def save_memory(self, memory: CuratedMemory) -> CuratedMemory:
        path = self._path(memory.memory_id)
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(self._sanitize(_dump(memory)), ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(path)
        return memory

    def get_memory(self, memory_id: str) -> CuratedMemory | None:
        path = self._path(memory_id)
        if not path.exists():
            return None
        return _parse_memory(json.loads(path.read_text(encoding="utf-8")))

    def list_memories(self, *, status: str | None = None, kind: str | None = None, scope: str | None = None, workspace: str | None = None, source_type: str | None = None, confidence: str | None = None, risk: str | None = None, text: str | None = None, tag: str | None = None, limit: int = 100) -> list[CuratedMemory]:
        memories: list[CuratedMemory] = []
        for path in sorted(self.root.glob("memory_*.json"), reverse=True):
            if path.name.endswith((".events.json", ".trace.json", ".versions.json")):
                continue
            memory = _parse_memory(json.loads(path.read_text(encoding="utf-8")))
            if status and memory.status != status:
                continue
            if kind and memory.kind != kind:
                continue
            if scope and memory.scope.scope_type != scope:
                continue
            if workspace and memory.scope.workspace != workspace:
                continue
            if source_type and memory.source.source_type != source_type:
                continue
            if confidence and memory.confidence != confidence:
                continue
            if risk and memory.risk.level != risk:
                continue
            if tag and tag not in memory.tags:
                continue
            if text and text.lower() not in f"{memory.summary} {memory.text}".lower():
                continue
            memories.append(memory)
            if len(memories) >= limit:
                break
        return memories

    def append_event(self, memory_id: str, event_type: str, status: str, message: str, metadata: dict[str, Any] | None = None) -> None:
        events = self.get_events(memory_id)
        events.append(CuratedMemoryEvent(event_id=f"memory_evt_{len(events)+1}", memory_id=memory_id, event_type=event_type, status=status, message=message, created_at=utc_now(), metadata=self._sanitize(metadata or {})))
        self._events_path(memory_id).write_text(json.dumps(self._sanitize([_dump(item) for item in events]), ensure_ascii=False, indent=2), encoding="utf-8")

    def get_events(self, memory_id: str) -> list[CuratedMemoryEvent]:
        path = self._events_path(memory_id)
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        return [CuratedMemoryEvent.model_validate(item) if hasattr(CuratedMemoryEvent, "model_validate") else CuratedMemoryEvent.parse_obj(item) for item in data]

    def save_trace(self, memory_id: str, trace: list[CuratedMemoryTrace]) -> None:
        self._trace_path(memory_id).write_text(json.dumps([_dump(item) for item in trace], ensure_ascii=False, indent=2), encoding="utf-8")

    def get_trace(self, memory_id: str) -> list[dict[str, Any]]:
        path = self._trace_path(memory_id)
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []

    def save_versions(self, memory_id: str, versions: list[CuratedMemoryVersion]) -> None:
        self._versions_path(memory_id).write_text(json.dumps([_dump(item) for item in versions], ensure_ascii=False, indent=2), encoding="utf-8")

    def get_versions(self, memory_id: str) -> list[CuratedMemoryVersion]:
        path = self._versions_path(memory_id)
        if not path.exists():
            memory = self.get_memory(memory_id)
            if memory is None:
                return []
            return [CuratedMemoryVersion(memory_id=memory_id, version=memory.version, status=memory.status, created_at=memory.created_at, candidate_id=memory.source.candidate_id, approval_id=memory.source.approval_id, summary_hash=self._hash(memory.summary), supersedes=memory.supersedes)]
        data = json.loads(path.read_text(encoding="utf-8"))
        return [CuratedMemoryVersion.model_validate(item) if hasattr(CuratedMemoryVersion, "model_validate") else CuratedMemoryVersion.parse_obj(item) for item in data]

    def status(self) -> dict[str, Any]:
        counts: dict[str, int] = {}
        kinds: dict[str, int] = {}
        for memory in self.list_memories(limit=10000):
            counts[memory.status] = counts.get(memory.status, 0) + 1
            kinds[memory.kind] = kinds.get(memory.kind, 0) + 1
        return {"status": "ok", "store": "local_json", "path": str(self.root), "counts_by_status": counts, "counts_by_kind": kinds, "search_mode": "deterministic", "vectorstore_enabled": False, "embeddings_enabled": False, "rag_enabled": False}

    def _hash(self, text: str) -> str:
        import hashlib

        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _sanitize(self, payload: Any) -> Any:
        if isinstance(payload, dict):
            sanitized: dict[str, Any] = {}
            for key, value in payload.items():
                if re.search(r"(?i)(api[_-]?key|token|password|passwd|secret)", str(key)):
                    sanitized[key] = "[REDACTED]"
                else:
                    sanitized[key] = self._sanitize(value)
            return sanitized
        if isinstance(payload, list):
            return [self._sanitize(item) for item in payload]
        if isinstance(payload, str):
            redacted = re.sub(r"(?i)(api[_-]?key|token|password|passwd|secret)\s*[:=]\s*['\"]?([A-Za-z0-9_\-]{6,})", r"\1=[REDACTED]", payload)
            return re.sub(r"sk-[A-Za-z0-9]{12,}", "sk-[REDACTED]", redacted)
        return payload
