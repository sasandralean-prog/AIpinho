from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


RuntimeObservationStatus = Literal["observed", "missing", "unavailable", "not_applicable"]
RegressionSeverity = Literal["info", "low", "medium", "high", "critical"]
RegressionCategory = Literal[
    "TextIngress",
    "Encoding",
    "SemanticNormalization",
    "SemanticPropositions",
    "StateEffects",
    "IntentCandidates",
    "IntentArbitration",
    "OperationContractSelection",
    "Intent",
    "Lifecycle",
    "Workspace",
    "Artifacts",
    "Approval",
    "Validation",
    "Completion",
    "SpeakerTruth",
    "Dispatcher",
    "SemanticIR",
    "ExecutionPlan",
    "Contracts",
    "RoleSelection",
    "Timeline",
    "Executor",
    "Models",
    "Tools",
    "Skills",
]
RegressionStatus = Literal["PASS", "WARN", "FAIL", "NOT_APPLICABLE"]


class RuntimeObservation(AIpinhoModel):
    name: str
    status: RuntimeObservationStatus = "observed"
    value: Any | None = None
    source: str | None = None
    warnings: list[str] = Field(default_factory=list)


class RuntimeSnapshot(AIpinhoModel):
    snapshot_id: str = Field(default_factory=lambda: f"runtime_snapshot_{uuid4().hex}")
    task_id: str | None = None
    task_run_id: str | None = None
    operation_id: str | None = None
    session_id: str | None = None
    current_intent: RuntimeObservation = Field(default_factory=lambda: RuntimeObservation(name="intent", status="missing"))
    current_lifecycle: RuntimeObservation = Field(default_factory=lambda: RuntimeObservation(name="lifecycle", status="missing"))
    current_contracts: RuntimeObservation = Field(default_factory=lambda: RuntimeObservation(name="contracts", status="missing"))
    current_roles: RuntimeObservation = Field(default_factory=lambda: RuntimeObservation(name="roles", status="missing"))
    current_workspace: RuntimeObservation = Field(default_factory=lambda: RuntimeObservation(name="workspace", status="missing"))
    current_validation: RuntimeObservation = Field(default_factory=lambda: RuntimeObservation(name="validation", status="missing"))
    current_completion: RuntimeObservation = Field(default_factory=lambda: RuntimeObservation(name="completion", status="missing"))
    current_speaker_truth: RuntimeObservation = Field(default_factory=lambda: RuntimeObservation(name="speaker_truth", status="missing"))
    current_artifacts: RuntimeObservation = Field(default_factory=lambda: RuntimeObservation(name="artifacts", status="missing"))
    semantic_ir: RuntimeObservation = Field(default_factory=lambda: RuntimeObservation(name="semantic_ir", status="missing"))
    execution_plan: RuntimeObservation = Field(default_factory=lambda: RuntimeObservation(name="execution_plan", status="missing"))
    approval: RuntimeObservation = Field(default_factory=lambda: RuntimeObservation(name="approval", status="missing"))
    dispatcher: RuntimeObservation = Field(default_factory=lambda: RuntimeObservation(name="dispatcher", status="missing"))
    timeline: RuntimeObservation = Field(default_factory=lambda: RuntimeObservation(name="timeline", status="missing"))
    executor: RuntimeObservation = Field(default_factory=lambda: RuntimeObservation(name="executor", status="missing"))
    models: RuntimeObservation = Field(default_factory=lambda: RuntimeObservation(name="models", status="missing"))
    tools: RuntimeObservation = Field(default_factory=lambda: RuntimeObservation(name="tools", status="missing"))
    skills: RuntimeObservation = Field(default_factory=lambda: RuntimeObservation(name="skills", status="missing"))
    source_refs: list[str] = Field(default_factory=list)
    read_only: bool = True
    side_effects: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ExpectedRuntimeContract(AIpinhoModel):
    intent: Any | None = None
    lifecycle: Any | None = None
    workspace: Any | None = None
    artifacts: Any | None = None
    approval: Any | None = None
    validation: Any | None = None
    completion: Any | None = None
    speaker_truth: Any | None = None
    dispatcher: Any | None = None
    timeline: Any | None = None
    semantic_ir: Any | None = None
    execution_plan: Any | None = None
    contracts: Any | None = None
    roles: Any | None = None
    executor: Any | None = None
    models: Any | None = None
    tools: Any | None = None
    skills: Any | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuntimeOperatorSnapshotRequest(AIpinhoModel):
    task_run_id: str | None = None
    runtime_data: dict[str, Any] = Field(default_factory=dict)


class RuntimeDoctorAnalyzeRequest(AIpinhoModel):
    snapshot: RuntimeSnapshot | None = None
    expected: ExpectedRuntimeContract = Field(default_factory=ExpectedRuntimeContract)
    runtime_data: dict[str, Any] = Field(default_factory=dict)
    task_run_id: str | None = None


class RegressionFinding(AIpinhoModel):
    finding_id: str = Field(default_factory=lambda: f"regression_{uuid4().hex}")
    category: RegressionCategory
    severity: RegressionSeverity = "medium"
    expected: Any | None = None
    actual: Any | None = None
    status: RegressionStatus = "FAIL"
    reason_code: str
    summary: str
    evidence_refs: list[str] = Field(default_factory=list)
    suspected_modules: list[str] = Field(default_factory=list)


class RegressionMatrixRow(AIpinhoModel):
    category: RegressionCategory
    status: RegressionStatus
    severity: RegressionSeverity = "info"
    reason_code: str | None = None


class RegressionMatrix(AIpinhoModel):
    rows: list[RegressionMatrixRow] = Field(default_factory=list)

    def status_for(self, category: RegressionCategory) -> RegressionStatus | None:
        for row in self.rows:
            if row.category == category:
                return row.status
        return None


class DoctorEvidence(AIpinhoModel):
    evidence_id: str = Field(default_factory=lambda: f"doctor_evidence_{uuid4().hex}")
    domain: RegressionCategory
    source: str
    observed: Any | None = None
    expected: Any | None = None
    refs: list[str] = Field(default_factory=list)


class DoctorRecommendation(AIpinhoModel):
    recommendation_id: str = Field(default_factory=lambda: f"doctor_recommendation_{uuid4().hex}")
    domain: RegressionCategory
    priority: RegressionSeverity = "medium"
    action: str
    rationale: str
    target_audience: Literal["runtime", "codex", "operator"] = "codex"


class DoctorSummary(AIpinhoModel):
    status: Literal["PASS", "WARN", "FAIL"] = "PASS"
    pass_count: int = 0
    warn_count: int = 0
    fail_count: int = 0
    not_applicable_count: int = 0
    highest_severity: RegressionSeverity = "info"


class DoctorMetadata(AIpinhoModel):
    doctor_version: str = "RD4.0"
    deterministic: bool = True
    read_only: bool = True
    side_effects: bool = False
    generated_artifacts: list[str] = Field(default_factory=lambda: ["runtime_doctor_report.json", "runtime_doctor.md"])


class RuntimeDoctorReport(AIpinhoModel):
    report_id: str = Field(default_factory=lambda: f"runtime_doctor_report_{uuid4().hex}")
    snapshot_id: str
    status: Literal["passed", "regressions_found"] = "passed"
    summary: DoctorSummary = Field(default_factory=DoctorSummary)
    matrix: RegressionMatrix = Field(default_factory=RegressionMatrix)
    findings: list[RegressionFinding] = Field(default_factory=list)
    evidence: list[DoctorEvidence] = Field(default_factory=list)
    recommendations: list[DoctorRecommendation] = Field(default_factory=list)
    metadata: DoctorMetadata = Field(default_factory=DoctorMetadata)
    markdown: str | None = None
    csv: str | None = None
    deterministic: bool = True
    read_only: bool = True
    side_effects: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RuntimeExplanation(AIpinhoModel):
    explanation_id: str = Field(default_factory=lambda: f"runtime_explanation_{uuid4().hex}")
    report_id: str
    executive_summary: str
    regressions: list[str] = Field(default_factory=list)
    impact: list[str] = Field(default_factory=list)
    hypotheses: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    interpreter_role: str = "semantic_interpreter"
    recommended_model: str = "qwen2.5-7b-instruct"
    decision_made: bool = False
    patch_generated: bool = False
    read_only: bool = True
    side_effects: bool = False


class RuntimeDoctorExplainRequest(AIpinhoModel):
    report: RuntimeDoctorReport
    snapshot: RuntimeSnapshot | None = None


class PatchPlanItem(AIpinhoModel):
    module: str
    reason: str
    risk: RegressionSeverity = "medium"
    proposed_action: str
    rollback: str
    tests: list[str] = Field(default_factory=list)


class RuntimePatchPlan(AIpinhoModel):
    patch_plan_id: str = Field(default_factory=lambda: f"runtime_patch_plan_{uuid4().hex}")
    report_id: str
    status: Literal["planned", "no_patch_needed"] = "planned"
    confidence: float = 0.0
    risk: RegressionSeverity = "medium"
    affected_modules: list[str] = Field(default_factory=list)
    items: list[PatchPlanItem] = Field(default_factory=list)
    tests: list[str] = Field(default_factory=list)
    rollback: list[str] = Field(default_factory=list)
    patch_planner_role: str = "patch_planner"
    recommended_model: str = "qwen2.5-coder-7b"
    applies_patch: bool = False
    read_only: bool = True
    side_effects: bool = False


class RuntimeDoctorPatchPlanRequest(AIpinhoModel):
    report: RuntimeDoctorReport
    snapshot: RuntimeSnapshot | None = None
    source_hints: list[str] = Field(default_factory=list)


class FireTestDoctorAnalyzeRequest(AIpinhoModel):
    raw: dict[str, Any] = Field(default_factory=dict)
    expected: ExpectedRuntimeContract = Field(default_factory=ExpectedRuntimeContract)
    source_hints: list[str] = Field(default_factory=list)


class FireTestDoctorResult(AIpinhoModel):
    firetest_analysis_id: str = Field(default_factory=lambda: f"firetest_doctor_{uuid4().hex}")
    doctor_report: RuntimeDoctorReport
    regression_matrix: RegressionMatrix
    patch_plan: RuntimePatchPlan
    read_only: bool = True
    side_effects: bool = False
