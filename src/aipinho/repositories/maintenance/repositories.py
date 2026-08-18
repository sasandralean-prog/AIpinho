from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Generic, TypeVar

from aipinho.core.paths import PATHS
from aipinho.schemas.maintenance.contracts import (
    MaintenanceAudit,
    MaintenanceLessonCandidate,
    MaintenanceRun,
    MaintenanceTrace,
    RepairProposal,
)

T = TypeVar("T")


class JsonModelRepository(Generic[T]):
    model_type: type[T]
    folder: str

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or PATHS.project_root / "data" / "runtime" / "maintenance" / self.folder

    def save(self, value: T) -> T:
        self.root.mkdir(parents=True, exist_ok=True)
        identifier = self.identifier(value)
        payload = value.model_dump() if hasattr(value, "model_dump") else value.dict()
        (self.root / f"{identifier}.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )
        return value

    def get(self, identifier: str) -> T | None:
        path = self.root / f"{identifier}.json"
        if not path.exists():
            return None
        return self.model_type(**json.loads(path.read_text(encoding="utf-8")))

    def list(self) -> list[T]:
        if not self.root.exists():
            return []
        return [
            self.model_type(**json.loads(path.read_text(encoding="utf-8")))
            for path in sorted(self.root.glob("*.json"))
        ]

    def identifier(self, value: T) -> str:
        raise NotImplementedError


class MaintenanceRunRepository(JsonModelRepository[MaintenanceRun]):
    model_type = MaintenanceRun
    folder = "runs"

    def identifier(self, value: MaintenanceRun) -> str:
        return value.run_id


class MaintenanceTraceRepository(JsonModelRepository[MaintenanceTrace]):
    model_type = MaintenanceTrace
    folder = "traces"

    def identifier(self, value: MaintenanceTrace) -> str:
        return value.trace_id


class RepairProposalRepository(JsonModelRepository[RepairProposal]):
    model_type = RepairProposal
    folder = "repair_proposals"

    def identifier(self, value: RepairProposal) -> str:
        return value.proposal_id


class LessonCandidateRepository(JsonModelRepository[MaintenanceLessonCandidate]):
    model_type = MaintenanceLessonCandidate
    folder = "lessons"

    def identifier(self, value: MaintenanceLessonCandidate) -> str:
        return value.candidate_id


class MaintenanceAuditRepository:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or PATHS.project_root / "data" / "runtime" / "maintenance" / "audit"

    def append(self, value: MaintenanceAudit) -> MaintenanceAudit:
        self.root.mkdir(parents=True, exist_ok=True)
        with (self.root / "maintenance_audit.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(value.model_dump(), ensure_ascii=True) + "\n")
        return value


class InvariantRepository:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or PATHS.project_root / "data" / "runtime" / "maintenance" / "invariants"

    def save_result(self, result: Any) -> Any:
        self.root.mkdir(parents=True, exist_ok=True)
        payload = result.model_dump() if hasattr(result, "model_dump") else dict(result)
        (self.root / f"{payload['check_id']}.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )
        return result
