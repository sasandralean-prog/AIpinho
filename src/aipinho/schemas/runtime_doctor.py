from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


def runtime_doctor_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


RuntimeDoctorStatus = Literal["PASS", "FAIL", "BLOCKED", "PENDING_APPROVAL"]


class RuntimeDoctorExpectedContract(AIpinhoModel):
    expected_status: str | None = None
    intent_type: str | None = None
    operation_type: str | None = None
    contract_type: str | None = None
    runtime_profile: str | None = None
    requires_task: bool | None = None
    requires_approval: bool | None = None
    required_outputs: list[str] = Field(default_factory=list)
    required_artifacts: list[str] = Field(default_factory=list)
    required_raw_sections: list[str] = Field(
        default_factory=lambda: [
            "lifecycle",
            "intent",
            "operation_contract",
            "execution_plan",
            "task",
            "task_run",
            "validation",
            "completion",
            "speaker_truth",
        ]
    )
    invariants: dict[str, Any] = Field(default_factory=dict)


class RuntimeDoctorTestRequest(AIpinhoModel):
    prompt: str
    expected_contract: RuntimeDoctorExpectedContract = Field(default_factory=RuntimeDoctorExpectedContract)
    session_id: str | None = None
    workspace: str | None = None
    max_iterations: int = 1
    auto_apply_patch: bool = False
    source_channel: str = "runtime_doctor"


class RuntimeDoctorRawSnapshot(AIpinhoModel):
    raw_id: str = Field(default_factory=lambda: runtime_doctor_id("runtime_doctor_raw"))
    iteration_id: str
    status: str = "collected"
    chat_response: dict[str, Any] = Field(default_factory=dict)
    lifecycle: dict[str, Any] = Field(default_factory=dict)
    intent: dict[str, Any] = Field(default_factory=dict)
    operation_contract: dict[str, Any] = Field(default_factory=dict)
    execution_plan: dict[str, Any] = Field(default_factory=dict)
    approval: dict[str, Any] = Field(default_factory=dict)
    task: dict[str, Any] = Field(default_factory=dict)
    task_run: dict[str, Any] = Field(default_factory=dict)
    artifacts: dict[str, Any] = Field(default_factory=dict)
    validation: dict[str, Any] = Field(default_factory=dict)
    completion: dict[str, Any] = Field(default_factory=dict)
    speaker_truth: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    traces: list[dict[str, Any]] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)
    collected_at: str = Field(default_factory=utc_now_iso)


class RuntimeDoctorViolation(AIpinhoModel):
    violation_id: str = Field(default_factory=lambda: runtime_doctor_id("runtime_doctor_violation"))
    violation_type: str
    severity: str = "high"
    summary: str
    expected: Any = None
    observed: Any = None
    evidence_path: str = ""
    evidence: dict[str, Any] = Field(default_factory=dict)


class RuntimeDoctorAnalysis(AIpinhoModel):
    analysis_id: str = Field(default_factory=lambda: runtime_doctor_id("runtime_doctor_analysis"))
    status: RuntimeDoctorStatus
    violations: list[RuntimeDoctorViolation] = Field(default_factory=list)
    summary: str = ""
    analyzed_at: str = Field(default_factory=utc_now_iso)


class RuntimeDoctorRootCause(AIpinhoModel):
    cause_id: str = Field(default_factory=lambda: runtime_doctor_id("runtime_doctor_cause"))
    violation_id: str
    probable_component: str
    probable_files: list[str] = Field(default_factory=list)
    probable_functions: list[str] = Field(default_factory=list)
    confidence: str = "medium"
    impact: str = "unknown"
    evidence: dict[str, Any] = Field(default_factory=dict)


class RuntimeDoctorPatchPlan(AIpinhoModel):
    patch_id: str = Field(default_factory=lambda: runtime_doctor_id("runtime_doctor_patch"))
    status: str = "planned"
    files: list[str] = Field(default_factory=list)
    functions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    rollback: list[str] = Field(default_factory=list)
    strategy: list[str] = Field(default_factory=list)
    requires_approval: bool = True
    approval_id: str | None = None
    applied: bool = False
    blocked_reason: str | None = None


class RuntimeDoctorPatchExecution(AIpinhoModel):
    status: str
    patch_id: str
    applied: bool = False
    approval_required: bool = True
    approval_id: str | None = None
    message: str = ""
    changed_files: list[str] = Field(default_factory=list)


class RuntimeDoctorDiff(AIpinhoModel):
    diff_id: str = Field(default_factory=lambda: runtime_doctor_id("runtime_doctor_diff"))
    status: str = "not_run"
    removed_violations: list[str] = Field(default_factory=list)
    new_violations: list[str] = Field(default_factory=list)
    unchanged_violations: list[str] = Field(default_factory=list)


class RuntimeDoctorIteration(AIpinhoModel):
    iteration_id: str = Field(default_factory=lambda: runtime_doctor_id("runtime_doctor_iteration"))
    index: int
    status: RuntimeDoctorStatus = "FAIL"
    task_id: str | None = None
    task_run_id: str | None = None
    operation_id: str | None = None
    approval_ids: list[str] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    raw_snapshot: RuntimeDoctorRawSnapshot | None = None
    analysis: RuntimeDoctorAnalysis | None = None
    root_causes: list[RuntimeDoctorRootCause] = Field(default_factory=list)
    patch_plan: RuntimeDoctorPatchPlan | None = None
    patch_execution: RuntimeDoctorPatchExecution | None = None
    regression_diff: RuntimeDoctorDiff | None = None
    started_at: str = Field(default_factory=utc_now_iso)
    finished_at: str | None = None


class RuntimeDoctorRunResult(AIpinhoModel):
    doctor_run_id: str = Field(default_factory=lambda: runtime_doctor_id("runtime_doctor_run"))
    status: RuntimeDoctorStatus
    iterations: list[RuntimeDoctorIteration] = Field(default_factory=list)
    report_path: str | None = None
    report_artifact_id: str | None = None
    final_summary: str = ""
    created_at: str = Field(default_factory=utc_now_iso)

