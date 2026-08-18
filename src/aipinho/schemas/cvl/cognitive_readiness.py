from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import Field, model_validator

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.cvl.cognitive_validation_laboratory import (
    CoverageReport,
    DependencyGraph,
    SimulationResult,
)


CognitiveReadinessStatus = Literal["ready", "blocked", "invalid", "partial"]
CognitiveGoNoGoRecommendation = Literal[
    "GO",
    "GO_WITH_RISK",
    "NO_GO_EXPECTED_BLOCK",
    "NO_GO_MISSING_CAPABILITY",
    "NO_GO_INSUFFICIENT_OBSERVABILITY",
]
CognitiveCalibrationStatus = Literal["pending", "matched", "partial_match", "mismatch"]


class CognitiveReadinessDecision(AIpinhoModel):
    decision: CognitiveGoNoGoRecommendation
    confidence: float = 0.0
    rationale: str = ""
    expected_risk_level: str = "unknown"
    expected_blocking_frontier: str | None = None
    expected_blocking_component: str | None = None
    expected_blocking_reason_code: str | None = None
    safe_to_start_phase1: bool = False
    requires_user_override: bool = False


class CognitivePrediction(AIpinhoModel):
    prediction_id: str = Field(default_factory=lambda: f"cognitive_prediction_{uuid4().hex}")
    predicted_outcome: str
    predicted_frontier: str | None = None
    predicted_component: str | None = None
    predicted_contract: str | None = None
    predicted_capability: str | None = None
    predicted_observer: str | None = None
    predicted_reason_code: str | None = None
    predicted_blocking_stage: str | None = None
    predicted_failure_mode: str | None = None
    confidence: float = 0.0
    causal_chain: list[str] = Field(default_factory=list)
    critical_dependencies: list[str] = Field(default_factory=list)
    alternative_hypotheses: list[str] = Field(default_factory=list)
    false_positive_risks: list[str] = Field(default_factory=list)
    false_negative_risks: list[str] = Field(default_factory=list)


class CognitiveDependencyGraph(AIpinhoModel):
    graph: DependencyGraph
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    critical_path: list[str] = Field(default_factory=list)
    critical_dependencies: list[str] = Field(default_factory=list)
    expected_modules: list[str] = Field(default_factory=list)
    expected_contracts: list[str] = Field(default_factory=list)
    expected_capabilities: list[str] = Field(default_factory=list)
    expected_observers: list[str] = Field(default_factory=list)
    expected_artifacts: list[str] = Field(default_factory=list)
    expected_validation_gates: list[str] = Field(default_factory=list)
    expected_truth_gates: list[str] = Field(default_factory=list)
    possible_bottlenecks: list[str] = Field(default_factory=list)


class CognitiveCoverageReport(AIpinhoModel):
    coverage: CoverageReport
    coverage_by_domain: dict[str, float] = Field(default_factory=dict)
    overall_coverage: float = 0.0
    critical_coverage: float = 0.0
    coverage_confidence: float = 0.0
    unknown_areas: list[str] = Field(default_factory=list)
    weak_areas: list[str] = Field(default_factory=list)
    strong_areas: list[str] = Field(default_factory=list)
    coverage_reason_codes: list[str] = Field(default_factory=list)


class CognitiveSimulationResult(AIpinhoModel):
    simulation: SimulationResult
    simulation_id: str
    simulated_path: list[str] = Field(default_factory=list)
    simulated_steps: list[dict[str, Any]] = Field(default_factory=list)
    simulated_blocking_point: str | None = None
    simulated_reason_code: str | None = None
    simulated_confidence: float = 0.0
    contracts_involved: list[str] = Field(default_factory=list)
    capabilities_involved: list[str] = Field(default_factory=list)
    observers_required: list[str] = Field(default_factory=list)
    evidence_required: list[str] = Field(default_factory=list)
    artifacts_expected: list[str] = Field(default_factory=list)
    validation_expected: list[str] = Field(default_factory=list)
    truth_expected: list[str] = Field(default_factory=list)
    simulation_limitations: list[str] = Field(default_factory=list)


class CognitiveFrontierReport(AIpinhoModel):
    frontier_id: str = Field(default_factory=lambda: f"cognitive_frontier_{uuid4().hex}")
    primary_frontier: str | None = None
    secondary_frontiers: list[str] = Field(default_factory=list)
    frontier_chain: list[str] = Field(default_factory=list)
    frontier_confidence: float = 0.0
    why_this_frontier: str = ""
    what_would_move_frontier_forward: list[str] = Field(default_factory=list)
    required_capabilities: list[str] = Field(default_factory=list)
    required_observability: list[str] = Field(default_factory=list)
    required_runtime_changes: list[str] = Field(default_factory=list)


class CognitiveReadinessResult(AIpinhoModel):
    readiness_id: str = Field(default_factory=lambda: f"cognitive_readiness_{uuid4().hex}")
    firetest_id: str
    firetest_version: str
    phase: int = 0
    status: CognitiveReadinessStatus
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    input_prompt_hash: str
    workspace_ref: str | None = None
    context_ref: str | None = None
    runtime_executed: bool = False
    task_created: bool = False
    task_run_created: bool = False
    operation_created: bool = False
    operational_artifacts_created: bool = False
    decision: CognitiveReadinessDecision
    prediction: CognitivePrediction
    dependency_graph: CognitiveDependencyGraph
    coverage_report: CognitiveCoverageReport
    simulation_result: CognitiveSimulationResult
    frontier_report: CognitiveFrontierReport
    go_no_go_recommendation: CognitiveGoNoGoRecommendation
    confidence: float = 0.0
    reason_codes: list[str] = Field(default_factory=list)
    critical_dependencies: list[str] = Field(default_factory=list)
    expected_blockers: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    safe_to_start_phase1: bool = False
    profile_id: str | None = None
    profile_selection_method: str | None = None
    profile_selection_confidence: float = 0.0
    profile_selection_reason_codes: list[str] = Field(default_factory=list)
    report_paths: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _phase0_invariants(self) -> "CognitiveReadinessResult":
        if self.phase != 0:
            raise ValueError("cognitive_readiness_phase_must_be_zero")
        if any(
            (
                self.runtime_executed,
                self.task_created,
                self.task_run_created,
                self.operation_created,
                self.operational_artifacts_created,
            )
        ):
            raise ValueError("cognitive_readiness_phase0_must_not_create_runtime_state")
        return self


class CognitivePredictionCalibrationResult(AIpinhoModel):
    calibration_id: str = Field(default_factory=lambda: f"cognitive_calibration_{uuid4().hex}")
    readiness_id: str
    task_run_id: str
    actual_outcome: str | None = None
    actual_frontier: str | None = None
    actual_component: str | None = None
    actual_reason_code: str | None = None
    actual_contract: str | None = None
    actual_capability: str | None = None
    actual_causal_chain: list[str] = Field(default_factory=list)
    prediction_matched_outcome: bool = False
    prediction_matched_frontier: bool = False
    prediction_matched_component: bool = False
    prediction_matched_reason_code: bool = False
    prediction_matched_contract: bool = False
    prediction_matched_capability: bool = False
    prediction_matched_causal_chain: bool = False
    confidence_was_calibrated: bool = False
    confidence_error: float | None = None
    specificity_score: float = 0.0
    causal_accuracy_score: float = 0.0
    overall_accuracy_score: float = 0.0
    false_positive: bool = False
    false_negative: bool = False
    overconfidence: bool = False
    underconfidence: bool = False
    divergence_explanation: str = ""
    lessons: list[str] = Field(default_factory=list)
    status: CognitiveCalibrationStatus = "pending"
