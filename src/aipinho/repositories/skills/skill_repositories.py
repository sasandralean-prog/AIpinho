from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS


def _read(path: Path, default: Any) -> Any:
    if not path.exists() or not path.stat().st_size:
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True), encoding="utf-8")


class SkillRegistryRepository:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or PATHS.project_root / "data" / "runtime" / "skills" / "registry" / "registry.json"

    def save(self, entries: list[dict[str, Any]]) -> None:
        _write(self.path, entries)

    def list(self) -> list[dict[str, Any]]:
        return _read(self.path, [])


class SkillCatalogRepository:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or PATHS.project_root / "data" / "runtime" / "skills" / "catalog" / "catalog.json"

    def save(self, entries: list[dict[str, Any]]) -> None:
        _write(self.path, entries)

    def list(self) -> list[dict[str, Any]]:
        return _read(self.path, [])


class SkillTraceRepository:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or PATHS.project_root / "data" / "runtime" / "skills" / "traces"

    def save(self, trace: Any) -> Any:
        payload = trace.model_dump() if hasattr(trace, "model_dump") else dict(trace)
        self.root.mkdir(parents=True, exist_ok=True)
        _write(self.root / f"{payload['trace_id']}.json", payload)
        return trace

    def get(self, trace_id: str) -> dict[str, Any] | None:
        path = self.root / f"{trace_id}.json"
        return _read(path, None)


class SkillAuditRepository:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or PATHS.project_root / "data" / "runtime" / "skills" / "audit" / "audit.jsonl"

    def append(self, audit: Any) -> Any:
        payload = audit.model_dump() if hasattr(audit, "model_dump") else dict(audit)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
        return audit
