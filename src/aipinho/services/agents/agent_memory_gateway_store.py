from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.agents.memory import MemoryAccessLog, MemoryCandidate, MemoryNamespaceInfo, MemoryRecord
from aipinho.schemas.events.contracts import utc_now_iso


def _dump(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value.dict()


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists() or path.stat().st_size == 0:
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


class AgentMemoryGatewayStore:
    def __init__(self, root: Path | None = None) -> None:
        env_root = os.getenv("AIPINHO_AGENT_MEMORY_ROOT")
        self.root = root or (Path(env_root) if env_root else PATHS.project_root / "data" / "runtime" / "agent_memory_gateway")
        self.namespaces_path = self.root / "namespaces.json"
        self.records_path = self.root / "records.json"
        self.candidates_path = self.root / "candidates.json"
        self.access_log_path = self.root / "access.jsonl"

    def ensure_namespaces(self, namespaces: list[MemoryNamespaceInfo]) -> list[MemoryNamespaceInfo]:
        existing = {item.namespace: item for item in self.list_namespaces()}
        changed = False
        for namespace in namespaces:
            if namespace.namespace not in existing:
                existing[namespace.namespace] = namespace
                changed = True
        if changed:
            _write_json(self.namespaces_path, {"namespaces": [_dump(item) for item in existing.values()]})
        return self.list_namespaces()

    def list_namespaces(self) -> list[MemoryNamespaceInfo]:
        payload = _read_json(self.namespaces_path, {"namespaces": []})
        return [MemoryNamespaceInfo(**item) for item in payload.get("namespaces", [])]

    def get_namespace(self, namespace: str) -> MemoryNamespaceInfo | None:
        return next((item for item in self.list_namespaces() if item.namespace == namespace), None)

    def save_record(self, record: MemoryRecord) -> MemoryRecord:
        rows = [item for item in self.list_records(include_all=True) if item.memory_id != record.memory_id]
        record = record.model_copy(update={"updated_at": utc_now_iso()})
        rows.append(record)
        _write_json(self.records_path, {"records": [_dump(item) for item in rows]})
        return record

    def get_record(self, memory_id: str) -> MemoryRecord | None:
        return next((item for item in self.list_records(include_all=True) if item.memory_id == memory_id), None)

    def list_records(
        self,
        *,
        namespace: str | None = None,
        agent_id: str | None = None,
        workspace_id: str | None = None,
        project_id: str | None = None,
        validation_status: str | None = None,
        include_all: bool = False,
    ) -> list[MemoryRecord]:
        payload = _read_json(self.records_path, {"records": []})
        rows = [MemoryRecord(**item) for item in payload.get("records", [])]
        if not include_all:
            if namespace is not None:
                rows = [item for item in rows if item.namespace == namespace]
            if agent_id is not None:
                rows = [item for item in rows if item.agent_id == agent_id]
            if workspace_id is not None:
                rows = [item for item in rows if item.workspace_id == workspace_id]
            if project_id is not None:
                rows = [item for item in rows if item.project_id == project_id]
            if validation_status is not None:
                rows = [item for item in rows if item.validation_status == validation_status]
        return sorted(rows, key=lambda item: item.updated_at, reverse=True)

    def save_candidate(self, candidate: MemoryCandidate) -> MemoryCandidate:
        rows = [item for item in self.list_candidates(include_all=True) if item.candidate_id != candidate.candidate_id]
        rows.append(candidate)
        _write_json(self.candidates_path, {"candidates": [_dump(item) for item in rows]})
        return candidate

    def get_candidate(self, candidate_id: str) -> MemoryCandidate | None:
        return next((item for item in self.list_candidates(include_all=True) if item.candidate_id == candidate_id), None)

    def list_candidates(
        self,
        *,
        namespace: str | None = None,
        proposed_by_agent_id: str | None = None,
        status: str | None = None,
        include_all: bool = False,
    ) -> list[MemoryCandidate]:
        payload = _read_json(self.candidates_path, {"candidates": []})
        rows = [MemoryCandidate(**item) for item in payload.get("candidates", [])]
        if not include_all:
            if namespace is not None:
                rows = [item for item in rows if item.namespace == namespace]
            if proposed_by_agent_id is not None:
                rows = [item for item in rows if item.proposed_by_agent_id == proposed_by_agent_id]
            if status is not None:
                rows = [item for item in rows if item.status == status]
        return sorted(rows, key=lambda item: item.proposed_at, reverse=True)

    def append_access(self, access: MemoryAccessLog) -> MemoryAccessLog:
        self.access_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.access_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(_dump(access), ensure_ascii=True) + "\n")
        return access

    def list_access(self, *, memory_id: str | None = None, candidate_id: str | None = None, run_id: str | None = None, limit: int = 200) -> list[MemoryAccessLog]:
        if not self.access_log_path.exists():
            return []
        rows: list[MemoryAccessLog] = []
        with self.access_log_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(MemoryAccessLog(**json.loads(line)))
        if memory_id is not None:
            rows = [item for item in rows if item.memory_id == memory_id]
        if candidate_id is not None:
            rows = [item for item in rows if item.candidate_id == candidate_id]
        if run_id is not None:
            rows = [item for item in rows if item.run_id == run_id]
        return rows[-limit:]
