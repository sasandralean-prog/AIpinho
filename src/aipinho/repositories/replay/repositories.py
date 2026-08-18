from __future__ import annotations

import json
from pathlib import Path
from typing import Generic, TypeVar

from aipinho.core.paths import PATHS
from aipinho.schemas.replay.contracts import ReplayCase, ReplayDiff, ReplayRun, ReplaySnapshot, ReplayTrace

T = TypeVar("T")


class JsonRepository(Generic[T]):
    model_type: type[T]
    folder: str

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or PATHS.project_root / "data" / "runtime" / "replay" / self.folder

    def save(self, value: T) -> T:
        self.root.mkdir(parents=True, exist_ok=True)
        identifier = self.identifier(value)
        (self.root / f"{identifier}.json").write_text(json.dumps(value.model_dump(), indent=2, ensure_ascii=True), encoding="utf-8")
        return value

    def get(self, identifier: str) -> T | None:
        path = self.root / f"{identifier}.json"
        return self.model_type(**json.loads(path.read_text(encoding="utf-8"))) if path.exists() else None

    def list(self) -> list[T]:
        if not self.root.exists():
            return []
        return [self.model_type(**json.loads(path.read_text(encoding="utf-8"))) for path in sorted(self.root.glob("*.json"))]

    def identifier(self, value: T) -> str:
        raise NotImplementedError


class ReplaySnapshotRepository(JsonRepository[ReplaySnapshot]):
    model_type = ReplaySnapshot
    folder = "snapshots"
    def identifier(self, value: ReplaySnapshot) -> str: return value.metadata.snapshot_id


class ReplayCaseRepository(JsonRepository[ReplayCase]):
    model_type = ReplayCase
    folder = "cases"
    def identifier(self, value: ReplayCase) -> str: return value.case_id


class ReplayRunRepository(JsonRepository[ReplayRun]):
    model_type = ReplayRun
    folder = "runs"
    def identifier(self, value: ReplayRun) -> str: return value.run_id


class ReplayTraceRepository(JsonRepository[ReplayTrace]):
    model_type = ReplayTrace
    folder = "traces"
    def identifier(self, value: ReplayTrace) -> str: return value.trace_id


class ReplayDiffRepository(JsonRepository[ReplayDiff]):
    model_type = ReplayDiff
    folder = "runs/diffs"
    def identifier(self, value: ReplayDiff) -> str: return value.diff_id
