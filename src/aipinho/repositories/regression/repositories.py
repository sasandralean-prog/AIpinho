from __future__ import annotations

import json
from pathlib import Path
from typing import Generic, TypeVar

from aipinho.core.paths import PATHS
from aipinho.schemas.regression.contracts import RegressionCase, RegressionCaseCandidate, RegressionReport, RegressionRunResult, RegressionSuite, RegressionSuiteRun

T = TypeVar("T")


class JsonRepository(Generic[T]):
    model_type: type[T]
    folder: str
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or PATHS.project_root / "data" / "runtime" / "regression" / self.folder
    def save(self, value: T) -> T:
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / f"{self.identifier(value)}.json").write_text(json.dumps(value.model_dump(), indent=2, ensure_ascii=True), encoding="utf-8")
        return value
    def get(self, identifier: str) -> T | None:
        path = self.root / f"{identifier}.json"
        return self.model_type(**json.loads(path.read_text(encoding="utf-8"))) if path.exists() else None
    def list(self) -> list[T]:
        if not self.root.exists(): return []
        return [self.model_type(**json.loads(path.read_text(encoding="utf-8"))) for path in sorted(self.root.glob("*.json"))]
    def identifier(self, value: T) -> str:
        raise NotImplementedError


class RegressionCaseRepository(JsonRepository[RegressionCase]):
    model_type = RegressionCase
    folder = "cases"
    def identifier(self, value: RegressionCase) -> str: return value.case_id


class RegressionCandidateRepository(JsonRepository[RegressionCaseCandidate]):
    model_type = RegressionCaseCandidate
    folder = "candidates"
    def identifier(self, value: RegressionCaseCandidate) -> str: return value.candidate_id


class RegressionSuiteRepository(JsonRepository[RegressionSuite]):
    model_type = RegressionSuite
    folder = "suites"
    def identifier(self, value: RegressionSuite) -> str: return value.suite_id


class RegressionRunRepository(JsonRepository[RegressionRunResult]):
    model_type = RegressionRunResult
    folder = "runs"
    def identifier(self, value: RegressionRunResult) -> str: return value.run_id


class RegressionReportRepository(JsonRepository[RegressionReport]):
    model_type = RegressionReport
    folder = "reports"
    def identifier(self, value: RegressionReport) -> str: return value.report_id
