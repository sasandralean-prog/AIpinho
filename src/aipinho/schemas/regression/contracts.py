from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.replay.contracts import utc_now_iso


def prefixed_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class GoldenExpectation(AIpinhoModel):
    expectation_id: str = Field(default_factory=lambda: prefixed_id("golden_expectation"))
    expectation_type: str
    assertions: dict[str, Any]
    expected_status: str = "passed"
    tolerance: str = "exact"
    failure_severity: str = "high"


class ExpectationResult(AIpinhoModel):
    expectation_id: str
    expectation_type: str
    status: str
    expected: dict[str, Any] = Field(default_factory=dict)
    actual: dict[str, Any] = Field(default_factory=dict)
    differences: list[dict[str, Any]] = Field(default_factory=list)
    severity: str = "info"


class RegressionFailure(AIpinhoModel):
    failure_id: str = Field(default_factory=lambda: prefixed_id("regression_failure"))
    expectation_id: str
    severity: str
    summary: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)


class RegressionDiff(AIpinhoModel):
    diff_id: str = Field(default_factory=lambda: prefixed_id("regression_diff"))
    differences: list[dict[str, Any]] = Field(default_factory=list)


class RegressionCase(AIpinhoModel):
    case_id: str = Field(default_factory=lambda: prefixed_id("regression_case"))
    title: str
    category: str
    replay_case_id: str | None = None
    snapshot_id: str | None = None
    expectations: list[GoldenExpectation] = Field(default_factory=list)
    status: str = "enabled"
    created_at: str = Field(default_factory=utc_now_iso)


class RegressionCaseCandidate(AIpinhoModel):
    candidate_id: str = Field(default_factory=lambda: prefixed_id("regression_candidate"))
    source_type: str
    category: str
    severity: str
    evidence: list[dict[str, Any]]
    expected_behavior: dict[str, Any]
    snapshot_id: str | None = None
    promoted: bool = False
    status: str = "candidate"
    created_at: str = Field(default_factory=utc_now_iso)


class RegressionPromotionRequest(AIpinhoModel):
    candidate_id: str
    approved: bool = False
    validation_passed: bool = False
    title: str | None = None


class RegressionPromotionResult(AIpinhoModel):
    status: str
    case: RegressionCase | None = None
    reasons: list[str] = Field(default_factory=list)


class RegressionSuite(AIpinhoModel):
    suite_id: str
    enabled: bool = True
    description: str = ""
    cases: list[RegressionCase] = Field(default_factory=list)


class RegressionSuiteRun(AIpinhoModel):
    suite_run_id: str = Field(default_factory=lambda: prefixed_id("regression_suite_run"))
    suite_id: str
    status: str
    case_results: list[dict[str, Any]] = Field(default_factory=list)
    report_id: str | None = None
    side_effects_performed: bool = False
    created_at: str = Field(default_factory=utc_now_iso)


class RegressionRunResult(AIpinhoModel):
    run_id: str = Field(default_factory=lambda: prefixed_id("regression_run"))
    case_id: str
    status: str
    expectation_results: list[ExpectationResult] = Field(default_factory=list)
    failures: list[RegressionFailure] = Field(default_factory=list)
    replay_run_id: str | None = None
    side_effects_performed: bool = False
    created_at: str = Field(default_factory=utc_now_iso)


class RegressionReport(AIpinhoModel):
    report_id: str = Field(default_factory=lambda: prefixed_id("regression_report"))
    run_id: str
    status: str
    summary: str
    failures: list[RegressionFailure] = Field(default_factory=list)
    expectation_results: list[ExpectationResult] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)


class RegressionStatus(AIpinhoModel):
    status: str = "ok"
    enabled: bool = True
    side_effects_allowed: bool = False
    golden_expectations_enabled: bool = True
    core_regression_suite_enabled: bool = True
    legacy_bug_regression_suite_enabled: bool = True
    safety_regression_suite_enabled: bool = True
    ux_regression_suite_enabled: bool = True
