from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field, model_validator

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


WorkflowType = Literal[
    "sandbox_creation",
    "project_analysis",
    "project_improvement",
    "project_debugging",
    "docs_generation",
    "artifact_recovery",
    "promotion_workflow",
    "release_readiness",
    "mobile_ux_audit",
    "external_workspace_onboarding",
    "bridge_provider_workflow",
    "mixed",
]
WorkflowMode = Literal["assisted_execution", "governed_autopilot", "supervised_autorun"]
WorkflowStatus = Literal[
    "created",
    "planning",
    "waiting_for_approval",
    "running",
    "paused",
    "resuming",
    "validating",
    "recovering",
    "reporting",
    "completed",
    "completed_with_warnings",
    "blocked",
    "validation_failed",
    "failed",
    "cancelled",
    "timed_out",
]
WorkflowPhaseStatus = Literal["created", "running", "completed", "skipped", "blocked", "failed", "cancelled"]
WorkflowStepStatus = Literal[
    "created",
    "planned",
    "previewed",
    "approved",
    "running",
    "completed",
    "completed_with_warnings",
    "skipped",
    "blocked",
    "failed",
    "waiting_for_approval",
    "cancelled",
    "timed_out",
]
WorkflowCheckpointType = Literal[
    "before_side_effect",
    "after_phase",
    "before_apply",
    "after_apply",
    "before_promotion",
    "after_validation",
    "before_cleanup",
    "recovery_point",
    "final",
]
WorkflowStepActionType = Literal[
    "route_decision",
    "project_profile_resolve",
    "workspace_onboarding",
    "sandbox_task_create",
    "skill_pack_execute",
    "tool_invoke",
    "file_generate",
    "shell_run",
    "validate",
    "artifact_export",
    "promotion_plan",
    "patch_preview",
    "approval_wait",
    "promotion_apply",
    "rollback_preview",
    "memory_extract",
    "report_generate",
]
WorkflowOnFailurePolicy = Literal["stop", "ask_user", "retry_once", "safe_recovery", "continue_with_warning", "fallback_to_dry_run", "fallback_to_report_only"]
WorkflowCheckpointRequiredAction = Literal["approve", "reject", "edit_plan", "continue", "cancel"]


class WorkflowWorkspaceContext(AIpinhoModel):
    source_workspace_id: str | None = None
    target_workspace_id: str | None = None
    sandbox_workspace_id: str | None = "sandbox_ws_default"
    workspace_role: str | None = None
    external_path_detected: bool = False
    onboarding_required: bool = False
    write_allowed: bool = False
    reasons: list[str] = Field(default_factory=list)


class WorkflowStopCondition(AIpinhoModel):
    condition_id: str = Field(default_factory=lambda: f"workflow_stop_{uuid4().hex}")
    kind: str
    threshold: int | str | None = None
    triggered: bool = False
    reason: str | None = None


class WorkflowStep(AIpinhoModel):
    step_id: str = Field(default_factory=lambda: f"workflow_step_{uuid4().hex}")
    phase_id: str
    index: int
    name: str
    objective: str
    action_type: WorkflowStepActionType
    title: str | None = None
    provider_id: str | None = None
    capability_id: str | None = None
    operation: str | None = None
    input_sanitized: dict[str, Any] = Field(default_factory=dict)
    source_scope: str = "unknown"
    expected_outputs: list[str] = Field(default_factory=list)
    target_agent_id: str = "autopilot"
    skill_pack_id: str | None = None
    skill_id: str | None = None
    tool_name: str | None = None
    status: WorkflowStepStatus = "created"
    risk_level: str = "low"
    approval_required: bool = False
    requires_preview: bool = False
    requires_approval: bool = False
    side_effects_expected: bool = False
    timeout_seconds: int = 60
    output_limit_kb: int = 64
    dependencies: list[str] = Field(default_factory=list)
    on_failure: WorkflowOnFailurePolicy = "stop"
    policy_decision_id: str | None = None
    tool_invocation_ids: list[str] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    validation_id: str | None = None
    checkpoint_id: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    started_at: str | None = None
    completed_at: str | None = None
    error: str | None = None
    warnings: list[str] = Field(default_factory=list)
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _sync_flags(self) -> "WorkflowStep":
        if self.title is None:
            self.title = self.name
        if self.requires_approval and not self.approval_required:
            self.approval_required = True
        if self.approval_required and not self.requires_approval:
            self.requires_approval = True
        return self


class WorkflowStepResult(AIpinhoModel):
    step_result_id: str = Field(default_factory=lambda: f"workflow_step_result_{uuid4().hex}")
    workflow_run_id: str
    step_id: str
    provider_id: str | None = None
    capability_id: str | None = None
    tool_name: str | None = None
    operation: str | None = None
    source_scope: str = "unknown"
    status: WorkflowStepStatus = "planned"
    policy_decision_id: str | None = None
    approval_id: str | None = None
    input_summary: str | None = None
    output_summary: str | None = None
    artifacts: list[str] = Field(default_factory=list)
    logs: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    started_at: str | None = None
    completed_at: str | None = None
    duration_ms: int | None = None
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class WorkflowPhase(AIpinhoModel):
    phase_id: str = Field(default_factory=lambda: f"workflow_phase_{uuid4().hex}")
    workflow_run_id: str | None = None
    index: int
    name: str
    objective: str
    status: WorkflowPhaseStatus = "created"
    required: bool = True
    steps: list[WorkflowStep] = Field(default_factory=list)
    checkpoint_before_id: str | None = None
    checkpoint_after_id: str | None = None
    validation_id: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    started_at: str | None = None
    completed_at: str | None = None


class WorkflowPlan(AIpinhoModel):
    workflow_plan_id: str = Field(default_factory=lambda: f"workflow_plan_{uuid4().hex}")
    workflow_id: str | None = None
    session_id: str | None = None
    requesting_agent_id: str = "aipinho"
    title: str | None = None
    objective: str | None = None
    user_goal: str
    workflow_type: WorkflowType = "mixed"
    mode: WorkflowMode = "assisted_execution"
    project_profile_id: str | None = None
    workspace_context: WorkflowWorkspaceContext = Field(default_factory=WorkflowWorkspaceContext)
    sandbox_context: dict[str, Any] = Field(default_factory=dict)
    source_scope: str = "unknown"
    workspace_ref: str | None = None
    risk_budget: dict[str, Any] = Field(default_factory=dict)
    approval_policy: dict[str, Any] = Field(default_factory=dict)
    target_workspace_id: str | None = None
    source_workspace_id: str | None = None
    selected_skill_packs: list[str] = Field(default_factory=list)
    selected_skills: list[str] = Field(default_factory=list)
    phases: list[WorkflowPhase] = Field(default_factory=list)
    expected_artifacts: list[str] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    expected_memory_candidates: list[str] = Field(default_factory=list)
    validation_strategy: list[str] = Field(default_factory=list)
    approval_strategy: list[str] = Field(default_factory=list)
    recovery_strategy: list[str] = Field(default_factory=list)
    stop_conditions: list[WorkflowStopCondition] = Field(default_factory=list)
    risk_assessment: dict[str, Any] = Field(default_factory=dict)
    limits: dict[str, Any] = Field(default_factory=dict)
    assumptions: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _sync_identity(self) -> "WorkflowPlan":
        if self.workflow_id is None:
            self.workflow_id = self.workflow_plan_id
        if self.title is None:
            self.title = self.user_goal[:120]
        if self.objective is None:
            self.objective = self.user_goal
        return self


class WorkflowPlanCreateRequest(AIpinhoModel):
    session_id: str | None = None
    requesting_agent_id: str = "aipinho"
    user_goal: str
    workflow_type: WorkflowType | None = None
    mode: WorkflowMode = "assisted_execution"
    project_profile_id: str | None = None
    source_workspace_id: str | None = None
    target_workspace_id: str | None = None
    sandbox_workspace_id: str = "sandbox_ws_default"
    project_stack: str | None = None
    requested_capabilities: list[str] = Field(default_factory=list)
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class WorkflowRun(AIpinhoModel):
    workflow_run_id: str = Field(default_factory=lambda: f"workflow_run_{uuid4().hex}")
    run_id: str | None = None
    workflow_plan_id: str
    workflow_id: str | None = None
    session_id: str | None = None
    gateway_session_id: str | None = None
    gateway_run_id: str | None = None
    initiating_agent_id: str = "aipinho"
    status: WorkflowStatus = "created"
    current_phase_id: str | None = None
    current_step_id: str | None = None
    current_step_result_id: str | None = None
    workflow_type: WorkflowType = "mixed"
    mode: WorkflowMode = "assisted_execution"
    project_profile_id: str | None = None
    sandbox_task_ids: list[str] = Field(default_factory=list)
    target_workspace_id: str | None = None
    source_workspace_id: str | None = None
    skill_pack_execution_ids: list[str] = Field(default_factory=list)
    skill_execution_ids: list[str] = Field(default_factory=list)
    tool_invocation_ids: list[str] = Field(default_factory=list)
    policy_decision_ids: list[str] = Field(default_factory=list)
    validation_ids: list[str] = Field(default_factory=list)
    checkpoint_ids: list[str] = Field(default_factory=list)
    step_result_ids: list[str] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    promotion_plan_ids: list[str] = Field(default_factory=list)
    memory_candidate_ids: list[str] = Field(default_factory=list)
    recovery_plan_ids: list[str] = Field(default_factory=list)
    stop_conditions_triggered: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    started_at: str = Field(default_factory=utc_now_iso)
    completed_at: str | None = None
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _sync_run_identity(self) -> "WorkflowRun":
        if self.run_id is None:
            self.run_id = self.workflow_run_id
        if self.workflow_id is None:
            self.workflow_id = self.workflow_plan_id
        return self


class WorkflowRunCreateRequest(AIpinhoModel):
    workflow_plan_id: str
    initiating_agent_id: str = "aipinho"
    autorun: bool = True
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class WorkflowCheckpoint(AIpinhoModel):
    checkpoint_id: str = Field(default_factory=lambda: f"workflow_checkpoint_{uuid4().hex}")
    workflow_run_id: str
    workflow_id: str | None = None
    phase_id: str | None = None
    step_id: str | None = None
    checkpoint_type: WorkflowCheckpointType
    status: str = "created"
    reason: str | None = None
    required_action: WorkflowCheckpointRequiredAction | None = None
    summary: str | None = None
    risk_notes: list[str] = Field(default_factory=list)
    artifacts_to_review: list[str] = Field(default_factory=list)
    state_snapshot_ref: str | None = None
    artifacts_snapshot: list[str] = Field(default_factory=list)
    files_snapshot: list[str] = Field(default_factory=list)
    memory_snapshot: list[str] = Field(default_factory=list)
    policy_state: dict[str, Any] = Field(default_factory=dict)
    validation_state: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now_iso)
    evidence_refs: list[str] = Field(default_factory=list)
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class WorkflowResumeRequest(AIpinhoModel):
    checkpoint_id: str | None = None
    reason: str = "resume_requested"
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class WorkflowCancelRequest(AIpinhoModel):
    reason: str = "user_cancelled"
    generate_partial_report: bool = True
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class WorkflowRecoveryPlan(AIpinhoModel):
    recovery_plan_id: str = Field(default_factory=lambda: f"workflow_recovery_{uuid4().hex}")
    workflow_run_id: str
    failed_step_id: str | None = None
    failure_source: str
    failure_reason: str
    proposed_recovery: str
    proposed_action: str | None = None
    risk_level: str = "low"
    requires_approval: bool = False
    policy_decision: str | None = None
    steps: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)
    status: str = "proposed"
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class WorkflowReplayRecord(AIpinhoModel):
    replay_id: str = Field(default_factory=lambda: f"workflow_replay_{uuid4().hex}")
    workflow_run_id: str
    workflow_id: str | None = None
    mode: Literal["read_only", "reexecute_requires_approval"] = "read_only"
    status: str = "ready"
    summary: str
    step_result_ids: list[str] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)


class WorkflowFinalReport(AIpinhoModel):
    workflow_run_id: str
    workflow_id: str | None = None
    status: WorkflowStatus
    summary: str
    step_result_ids: list[str] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    validation_ids: list[str] = Field(default_factory=list)
    memory_candidate_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)


class WorkflowApproval(AIpinhoModel):
    approval_id: str = Field(default_factory=lambda: f"workflow_approval_{uuid4().hex}")
    workflow_run_id: str
    workflow_id: str | None = None
    step_id: str | None = None
    status: Literal["pending", "approved", "rejected"] = "pending"
    reason: str
    risk_level: str = "medium"
    preview_id: str | None = None
    command_id: str | None = None
    artifacts_to_review: list[str] = Field(default_factory=list)
    expected_side_effects: list[str] = Field(default_factory=list)
    validation_plan: list[str] = Field(default_factory=list)
    rollback_plan: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)
    decided_at: str | None = None
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)
