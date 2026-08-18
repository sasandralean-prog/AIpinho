from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


RegressionDomainStatus = Literal["PASS", "FAIL", "WARN", "NOT_APPLICABLE"]
RegressionSeverity = Literal["low", "medium", "high", "critical"]


class ExpectedRuntimeContract(AIpinhoModel):
    contract_id: str = Field(default_factory=lambda: f"expected_runtime_{uuid4().hex}")
    task_id: str | None = None
    task_run_id: str | None = None
    operation_id: str | None = None
    expected_intent: dict[str, Any] = Field(default_factory=dict)
    expected_operation: dict[str, Any] = Field(default_factory=dict)
    expected_runtime_profile: str | None = None
    expected_workspace_roots: list[str] = Field(default_factory=list)
    expected_artifacts: list[str] = Field(default_factory=list)
    expected_approval: dict[str, Any] = Field(default_factory=dict)
    expected_validation: dict[str, Any] = Field(default_factory=dict)
    expected_completion: dict[str, Any] = Field(default_factory=dict)
    expected_speaker_truth: dict[str, Any] = Field(default_factory=dict)
    expected_dispatcher_state: dict[str, Any] = Field(default_factory=dict)
    expected_timeline_events: list[str] = Field(default_factory=list)
    expected_lifecycle: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)


class RegressionFinding(AIpinhoModel):
    regression_id: str = Field(default_factory=lambda: f"regression_{uuid4().hex}")
    regression_type: str
    severity: RegressionSeverity = "medium"
    subsystem: str
    expected_value: Any = None
    actual_value: Any = None
    evidence_refs: list[str] = Field(default_factory=list)
    suspected_modules: list[str] = Field(default_factory=list)
    confidence: float = 1.0
    deterministic: bool = True


class RegressionMatrix(AIpinhoModel):
    text_ingress: RegressionDomainStatus = "NOT_APPLICABLE"
    encoding: RegressionDomainStatus = "NOT_APPLICABLE"
    semantic_normalization: RegressionDomainStatus = "NOT_APPLICABLE"
    semantic_propositions: RegressionDomainStatus = "NOT_APPLICABLE"
    state_effects: RegressionDomainStatus = "NOT_APPLICABLE"
    intent_candidates: RegressionDomainStatus = "NOT_APPLICABLE"
    intent_arbitration: RegressionDomainStatus = "NOT_APPLICABLE"
    operation_contract_selection: RegressionDomainStatus = "NOT_APPLICABLE"
    intent: RegressionDomainStatus = "NOT_APPLICABLE"
    inference: RegressionDomainStatus = "NOT_APPLICABLE"
    diagnosis: RegressionDomainStatus = "NOT_APPLICABLE"
    repair_intent: RegressionDomainStatus = "NOT_APPLICABLE"
    semantic_evidence: RegressionDomainStatus = "NOT_APPLICABLE"
    behavior_localization: RegressionDomainStatus = "NOT_APPLICABLE"
    behavior_justification: RegressionDomainStatus = "NOT_APPLICABLE"
    candidate_transformation: RegressionDomainStatus = "NOT_APPLICABLE"
    patch_candidate: RegressionDomainStatus = "NOT_APPLICABLE"
    actionability: RegressionDomainStatus = "NOT_APPLICABLE"
    prompt: RegressionDomainStatus = "NOT_APPLICABLE"
    completeness: RegressionDomainStatus = "NOT_APPLICABLE"
    context_budget: RegressionDomainStatus = "NOT_APPLICABLE"
    firetest_lab: RegressionDomainStatus = "NOT_APPLICABLE"
    prediction: RegressionDomainStatus = "NOT_APPLICABLE"
    dependency_graph: RegressionDomainStatus = "NOT_APPLICABLE"
    coverage: RegressionDomainStatus = "NOT_APPLICABLE"
    simulation: RegressionDomainStatus = "NOT_APPLICABLE"
    prediction_accuracy: RegressionDomainStatus = "NOT_APPLICABLE"
    simulation_accuracy: RegressionDomainStatus = "NOT_APPLICABLE"
    lifecycle: RegressionDomainStatus = "NOT_APPLICABLE"
    workspace_binding: RegressionDomainStatus = "NOT_APPLICABLE"
    artifact_contract: RegressionDomainStatus = "NOT_APPLICABLE"
    entity_compilation: RegressionDomainStatus = "NOT_APPLICABLE"
    contract_observation: RegressionDomainStatus = "NOT_APPLICABLE"
    entity_selection: RegressionDomainStatus = "NOT_APPLICABLE"
    observation_planning: RegressionDomainStatus = "NOT_APPLICABLE"
    observation_goal: RegressionDomainStatus = "NOT_APPLICABLE"
    observation_strategy: RegressionDomainStatus = "NOT_APPLICABLE"
    capability_registry: RegressionDomainStatus = "NOT_APPLICABLE"
    capability_matching: RegressionDomainStatus = "NOT_APPLICABLE"
    capability_arbitration: RegressionDomainStatus = "NOT_APPLICABLE"
    observer_capability: RegressionDomainStatus = "NOT_APPLICABLE"
    observer_execution: RegressionDomainStatus = "NOT_APPLICABLE"
    attribute_observation: RegressionDomainStatus = "NOT_APPLICABLE"
    evidence_recording: RegressionDomainStatus = "NOT_APPLICABLE"
    knowledge_representation: RegressionDomainStatus = "NOT_APPLICABLE"
    semantic_assertions: RegressionDomainStatus = "NOT_APPLICABLE"
    semantic_self_review: RegressionDomainStatus = "NOT_APPLICABLE"
    truth_readiness: RegressionDomainStatus = "NOT_APPLICABLE"
    coverage_analysis: RegressionDomainStatus = "NOT_APPLICABLE"
    artifact_renderer: RegressionDomainStatus = "NOT_APPLICABLE"
    schema_coverage: RegressionDomainStatus = "NOT_APPLICABLE"
    approval: RegressionDomainStatus = "NOT_APPLICABLE"
    validation: RegressionDomainStatus = "NOT_APPLICABLE"
    completion: RegressionDomainStatus = "NOT_APPLICABLE"
    speaker_truth: RegressionDomainStatus = "NOT_APPLICABLE"
    patch_planning: RegressionDomainStatus = "NOT_APPLICABLE"
    dispatcher: RegressionDomainStatus = "NOT_APPLICABLE"
    timeline: RegressionDomainStatus = "NOT_APPLICABLE"


class RuntimeDoctorArtifactRefs(AIpinhoModel):
    report_json_artifact_id: str | None = None
    report_markdown_artifact_id: str | None = None
    regression_matrix_csv_artifact_id: str | None = None


class RuntimeDoctorReport(AIpinhoModel):
    report_id: str = Field(default_factory=lambda: f"runtime_doctor_{uuid4().hex}")
    status: Literal["PASS", "FAIL", "WARN"] = "PASS"
    deterministic: bool = True
    expected_contract: ExpectedRuntimeContract
    matrix: RegressionMatrix
    findings: list[RegressionFinding] = Field(default_factory=list)
    artifact_refs: RuntimeDoctorArtifactRefs = Field(default_factory=RuntimeDoctorArtifactRefs)
    raw_runtime_summary: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    verdict: str = "RUNTIME_DOCTOR_READY"
