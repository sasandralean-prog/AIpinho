from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


CVLStatus = Literal["ready", "blocked", "partial", "not_applicable"]
CVLSeverity = Literal["info", "low", "medium", "high", "critical"]
DependencyNodeType = Literal["contract", "module", "capability", "artifact", "pipeline", "domain"]
SimulationStepStatus = Literal["predicted_success", "predicted_blocked", "predicted_skipped"]


class FireTestProfile(AIpinhoModel):
    profile_id: str = Field(default_factory=lambda: f"firetest_profile_{uuid4().hex}")
    name: str
    objective: str
    domain: str = "generic"
    expected_pipeline: list[str] = Field(default_factory=list)
    involved_contracts: list[str] = Field(default_factory=list)
    involved_modules: list[str] = Field(default_factory=list)
    expected_capabilities: list[str] = Field(default_factory=list)
    expected_artifacts: list[str] = Field(default_factory=list)
    success_contract: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class FireTestSuite(AIpinhoModel):
    suite_id: str = Field(default_factory=lambda: f"firetest_suite_{uuid4().hex}")
    name: str = "cognitive_validation_suite"
    profiles: list[FireTestProfile] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DependencyNode(AIpinhoModel):
    node_id: str
    node_type: DependencyNodeType
    label: str
    depends_on: list[str] = Field(default_factory=list)
    dependents: list[str] = Field(default_factory=list)
    impact: str = "unknown"
    criticality: CVLSeverity = "medium"
    metadata: dict[str, Any] = Field(default_factory=dict)


class DependencyGraph(AIpinhoModel):
    graph_id: str = Field(default_factory=lambda: f"dependency_graph_{uuid4().hex}")
    source_profile_id: str | None = None
    nodes: list[DependencyNode] = Field(default_factory=list)
    edges: list[dict[str, str]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DependencyImpactReport(AIpinhoModel):
    report_id: str = Field(default_factory=lambda: f"dependency_impact_{uuid4().hex}")
    source_node_id: str
    impacted_node_ids: list[str] = Field(default_factory=list)
    direct_dependents: list[str] = Field(default_factory=list)
    transitive_dependents: list[str] = Field(default_factory=list)
    impact_summary: str = ""
    criticality: CVLSeverity = "medium"


class PredictionReport(AIpinhoModel):
    prediction_id: str = Field(default_factory=lambda: f"prediction_{uuid4().hex}")
    profile_id: str
    predicted_status: CVLStatus = "ready"
    probable_component: str | None = None
    probable_contract: str | None = None
    probable_capability: str | None = None
    confidence: float = 0.0
    dependency_chain: list[str] = Field(default_factory=list)
    hypothesis: str = ""
    reason_codes: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class CoverageMetric(AIpinhoModel):
    domain: str
    coverage: float = 0.0
    confidence: float = 0.0
    health: CVLStatus = "not_applicable"
    criticality: CVLSeverity = "medium"
    gaps: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class CoverageReport(AIpinhoModel):
    report_id: str = Field(default_factory=lambda: f"coverage_report_{uuid4().hex}")
    profile_id: str | None = None
    metrics: list[CoverageMetric] = Field(default_factory=list)
    overall_coverage: float = 0.0
    overall_status: CVLStatus = "not_applicable"
    metadata: dict[str, Any] = Field(default_factory=dict)


class CoverageTrend(AIpinhoModel):
    trend_id: str = Field(default_factory=lambda: f"coverage_trend_{uuid4().hex}")
    domain: str
    points: list[dict[str, Any]] = Field(default_factory=list)
    direction: Literal["improving", "stable", "declining", "unknown"] = "unknown"


class SimulationRequest(AIpinhoModel):
    request_id: str = Field(default_factory=lambda: f"simulation_request_{uuid4().hex}")
    profile: FireTestProfile
    available_capabilities: list[str] = Field(default_factory=list)
    assumptions: dict[str, Any] = Field(default_factory=dict)


class PredictedFailure(AIpinhoModel):
    failure_id: str = Field(default_factory=lambda: f"predicted_failure_{uuid4().hex}")
    component: str
    reason_code: str
    summary: str
    confidence: float = 0.0
    dependency_chain: list[str] = Field(default_factory=list)


class PredictedSuccess(AIpinhoModel):
    success_id: str = Field(default_factory=lambda: f"predicted_success_{uuid4().hex}")
    component: str
    summary: str
    confidence: float = 0.0
    evidence_refs: list[str] = Field(default_factory=list)


class SimulationStep(AIpinhoModel):
    step_id: str = Field(default_factory=lambda: f"simulation_step_{uuid4().hex}")
    index: int
    component: str
    status: SimulationStepStatus
    expected_contracts: list[str] = Field(default_factory=list)
    required_capabilities: list[str] = Field(default_factory=list)
    reason_code: str | None = None
    explanation: str = ""
    confidence: float = 0.0


class SimulationResult(AIpinhoModel):
    simulation_id: str = Field(default_factory=lambda: f"simulation_{uuid4().hex}")
    request_id: str
    profile_id: str
    status: CVLStatus
    steps: list[SimulationStep] = Field(default_factory=list)
    predicted_failures: list[PredictedFailure] = Field(default_factory=list)
    predicted_successes: list[PredictedSuccess] = Field(default_factory=list)
    confidence: float = 0.0
    summary: str = ""


class CognitiveValidationLaboratoryResult(AIpinhoModel):
    result_id: str = Field(default_factory=lambda: f"cvl_result_{uuid4().hex}")
    suite: FireTestSuite
    dependency_graphs: list[DependencyGraph] = Field(default_factory=list)
    prediction_reports: list[PredictionReport] = Field(default_factory=list)
    coverage_reports: list[CoverageReport] = Field(default_factory=list)
    simulation_results: list[SimulationResult] = Field(default_factory=list)
    report_paths: dict[str, str] = Field(default_factory=dict)
    status: CVLStatus = "ready"
