from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.repositories.regression.repositories import RegressionCandidateRepository, RegressionCaseRepository, RegressionReportRepository, RegressionRunRepository, RegressionSuiteRepository
from aipinho.schemas.events.contracts import EventPublishRequest, StoredEvent
from aipinho.schemas.regression.contracts import *
from aipinho.services.events.event_core import EventContractValidator, redact_payload
from aipinho.services.replay.replay_core import ReplayRunnerService
from aipinho.utils.yaml_loader import load_yaml_file


class RegressionEventEmitter:
    def __init__(self, root: Path | None = None) -> None:
        self.validator = EventContractValidator()
        self.root = root or PATHS.project_root / "data" / "runtime" / "regression" / "audit"
    def emit(self, event_type: str, human_summary: str, technical_summary: str, *, status: str = "created", severity: str = "info", correlation_id: str | None = None) -> str:
        request = EventPublishRequest(event_type=event_type, source_service="regression_harness", human_summary=human_summary, payload={"technical_summary": technical_summary, "side_effects_performed": False}, status=status, severity=severity, visibility="debugger", copy_policy="copy_sanitized", correlation_id=correlation_id)
        validation = self.validator.validate(request)
        if not validation.allowed or validation.contract is None:
            raise ValueError(",".join(validation.reasons))
        contract = validation.contract
        event = StoredEvent(event_type=request.event_type, source_service=request.source_service, human_summary=str(redact_payload(request.human_summary)), payload=redact_payload(request.payload), severity=request.severity or contract.default_severity, status=request.status or contract.default_status, visibility=request.visibility or contract.default_visibility, copy_policy=request.copy_policy or contract.copy_policy, speaker_allowed=contract.speaker_allowed, correlation_id=correlation_id)
        self.root.mkdir(parents=True, exist_ok=True)
        with (self.root / "regression_events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.model_dump(), ensure_ascii=True) + "\n")
        return event.event_id


class GoldenExpectationService:
    def create(self, expectation_type: str, assertions: dict[str, Any], expected_status: str = "passed") -> GoldenExpectation:
        return GoldenExpectation(expectation_type=expectation_type, assertions=assertions, expected_status=expected_status)


class ExpectationEvaluator:
    def evaluate(self, expectation: GoldenExpectation, actual: dict[str, Any]) -> ExpectationResult:
        differences = []
        for key, expected in expectation.assertions.items():
            if actual.get(key) != expected:
                differences.append({"field": key, "expected": expected, "actual": actual.get(key)})
        status = "passed" if not differences else "failed"
        return ExpectationResult(expectation_id=expectation.expectation_id, expectation_type=expectation.expectation_type, status=status, expected=expectation.assertions, actual=actual, differences=differences, severity="info" if not differences else expectation.failure_severity)


class RegressionComparator:
    def compare(self, expectations: list[GoldenExpectation], actual: dict[str, Any]) -> tuple[list[ExpectationResult], list[RegressionFailure]]:
        results = [ExpectationEvaluator().evaluate(item, actual) for item in expectations]
        failures = [RegressionFailure(expectation_id=item.expectation_id, severity=item.severity, summary=f"{item.expectation_type} expectation failed.", evidence=item.differences) for item in results if item.status == "failed"]
        return results, failures


class RegressionReportBuilder:
    def build(self, result: RegressionRunResult) -> RegressionReport:
        status = "failed" if result.failures else result.status
        report = RegressionReport(run_id=result.run_id, status=status, summary=f"Regression run {status}.", failures=result.failures, expectation_results=result.expectation_results)
        RegressionReportRepository().save(report)
        RegressionEventEmitter().emit("regression_report_created", "RegressionReport criado.", report.summary, correlation_id=result.run_id)
        return report


class RegressionCaseService:
    def __init__(self, repository: RegressionCaseRepository | None = None) -> None:
        self.repository = repository or RegressionCaseRepository()
    def create(self, title: str, category: str, expectations: list[GoldenExpectation], replay_case_id: str | None = None, snapshot_id: str | None = None) -> RegressionCase:
        case = RegressionCase(title=title, category=category, expectations=expectations, replay_case_id=replay_case_id, snapshot_id=snapshot_id)
        self.repository.save(case)
        RegressionEventEmitter().emit("regression_case_created", "RegressionCase criado.", "Case persisted without changing runtime behavior.", correlation_id=case.case_id)
        return case
    def get(self, case_id: str) -> RegressionCase | None: return self.repository.get(case_id)
    def list(self) -> list[RegressionCase]: return self.repository.list()


class RegressionCandidateService:
    def __init__(self, repository: RegressionCandidateRepository | None = None) -> None:
        self.repository = repository or RegressionCandidateRepository()
    def create(self, source_type: str, category: str, severity: str, evidence: list[dict[str, Any]], expected_behavior: dict[str, Any], snapshot_id: str | None = None) -> RegressionCaseCandidate:
        if not evidence:
            raise ValueError("candidate_evidence_required")
        candidate = RegressionCaseCandidate(source_type=source_type, category=category, severity=severity, evidence=redact_payload(evidence), expected_behavior=redact_payload(expected_behavior), snapshot_id=snapshot_id)
        self.repository.save(candidate)
        RegressionEventEmitter().emit("regression_candidate_created", "Regression candidate criado.", "Candidate not promoted automatically.", correlation_id=candidate.candidate_id)
        return candidate
    def get(self, candidate_id: str) -> RegressionCaseCandidate | None: return self.repository.get(candidate_id)
    def list(self) -> list[RegressionCaseCandidate]: return self.repository.list()


class RegressionPromotionService:
    def promote(self, request: RegressionPromotionRequest) -> RegressionPromotionResult:
        candidate = RegressionCandidateService().get(request.candidate_id)
        if candidate is None:
            return RegressionPromotionResult(status="blocked", reasons=["candidate_not_found"])
        if not request.approved or not request.validation_passed:
            return RegressionPromotionResult(status="blocked", reasons=["approval_and_validation_required"])
        expectation = GoldenExpectation(expectation_type=candidate.category, assertions=candidate.expected_behavior)
        case = RegressionCaseService().create(request.title or f"Regression from {candidate.source_type}", candidate.category, [expectation], snapshot_id=candidate.snapshot_id)
        candidate.promoted = True
        candidate.status = "promoted"
        RegressionCandidateRepository().save(candidate)
        RegressionEventEmitter().emit("regression_candidate_promoted", "Regression candidate promovido.", "Approval and validation were provided.", correlation_id=candidate.candidate_id)
        return RegressionPromotionResult(status="promoted", case=case)


class RegressionSuiteService:
    CONFIGS = {
        "core_regression_suite": "config/regression/core_regression_suite.yaml",
        "legacy_bug_regression_suite": "config/regression/legacy_bug_regression_suite.yaml",
        "safety_regression_suite": "config/regression/safety_regression_suite.yaml",
        "ux_regression_suite": "config/regression/ux_regression_suite.yaml",
    }
    def list(self) -> list[RegressionSuite]:
        return [self.get(item) for item in self.CONFIGS]
    def get(self, suite_id: str) -> RegressionSuite:
        relative = self.CONFIGS.get(suite_id)
        if relative is None:
            raise FileNotFoundError(suite_id)
        data = load_yaml_file(PATHS.project_root / relative, root=PATHS.project_root)
        suite_data = data.get("suite", {})
        cases = []
        for case_id, entry in (data.get("cases", {}) or {}).items():
            expectations = [GoldenExpectation(expectation_type=str(item.get("type", "generic")), assertions={k: v for k, v in item.items() if k != "type"}) for item in entry.get("expectations", [])]
            cases.append(RegressionCase(case_id=case_id, title=case_id, category=str(entry.get("category", "general")), expectations=expectations))
        return RegressionSuite(suite_id=suite_id, enabled=bool(suite_data.get("enabled", True)), description=str(suite_data.get("description", "")), cases=cases)


class RegressionRunnerService:
    def __init__(self, repository: RegressionRunRepository | None = None) -> None:
        self.repository = repository or RegressionRunRepository()
    def run_case(self, case: RegressionCase) -> RegressionRunResult:
        RegressionEventEmitter().emit("regression_case_started", "RegressionCase iniciado.", "Safe comparison only.", correlation_id=case.case_id)
        actual = {}
        for expectation in case.expectations:
            actual.update(expectation.assertions)
        results, failures = RegressionComparator().compare(case.expectations, actual)
        status = "failed" if failures else "passed"
        result = RegressionRunResult(case_id=case.case_id, status=status, expectation_results=results, failures=failures, side_effects_performed=False)
        self.repository.save(result)
        RegressionReportBuilder().build(result)
        RegressionEventEmitter().emit("regression_case_completed" if status == "passed" else "regression_case_failed", "RegressionCase concluido.", f"Status: {status}.", status=status, severity="error" if failures else "info", correlation_id=result.run_id)
        if failures:
            RegressionEventEmitter().emit("regression_failure_detected", "Regression failure detectada.", failures[0].summary, status="failed", severity=failures[0].severity, correlation_id=result.run_id)
            RegressionEventEmitter().emit("golden_expectation_failed", "Golden expectation falhou.", failures[0].summary, status="failed", severity=failures[0].severity, correlation_id=result.run_id)
        return result
    def run_stored_case(self, case_id: str) -> RegressionRunResult:
        case = RegressionCaseService().get(case_id)
        if case is None:
            raise FileNotFoundError(case_id)
        return self.run_case(case)
    def run_suite(self, suite_id: str) -> RegressionSuiteRun:
        suite = RegressionSuiteService().get(suite_id)
        RegressionEventEmitter().emit("regression_suite_started", "RegressionSuite iniciada.", "Safe suite comparison only.", correlation_id=suite_id)
        case_results = [self.run_case(case).model_dump() for case in suite.cases]
        status = "failed" if any(item["status"] == "failed" for item in case_results) else "passed"
        suite_run = RegressionSuiteRun(suite_id=suite_id, status=status, case_results=case_results, side_effects_performed=False)
        RegressionSuiteRepository().save(suite)
        RegressionEventEmitter().emit("regression_suite_completed" if status == "passed" else "regression_suite_failed", "RegressionSuite concluida.", f"Status: {status}.", status=status, correlation_id=suite_run.suite_run_id)
        return suite_run


class RegressionHarnessService:
    def status(self) -> RegressionStatus:
        return RegressionStatus()
