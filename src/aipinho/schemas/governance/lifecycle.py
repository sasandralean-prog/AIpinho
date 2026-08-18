from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.intent.semantic_intent_graph import SemanticIntentGraph


class GovernanceLifecycleState(str, Enum):
    INTAKE = "intake"
    INTENT_RESOLVED = "intent_resolved"
    CONTRACT_CREATED = "contract_created"
    POLICY_RESOLVED = "policy_resolved"
    PLAN_ONLY_PREVIEW = "plan_only_preview"
    EXECUTABLE_PREVIEW = "executable_preview"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    EXECUTION_PLANNED = "execution_planned"
    RUNNING = "running"
    VALIDATING = "validating"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    BLOCKED = "blocked"
    FAILED = "failed"


class GovernanceLifecycleReasonCode(str, Enum):
    NONE = "none"
    READONLY_OR_PLANNING = "readonly_or_planning"
    APPROVAL_REQUIRED = "approval_required"
    POLICY_DENIED = "policy_denied"
    NEEDS_CLARIFICATION = "needs_clarification"
    INVALID_OPERATION = "invalid_operation"
    MISSING_EXECUTABLE_PLAN = "missing_executable_plan"
    APPROVAL_STALE = "approval_stale"
    APPROVAL_EXPIRED = "approval_expired"
    TASK_RUN_BLOCKED = "task_run_blocked"
    VALIDATION_MISSING_OUTPUTS = "validation_missing_outputs"
    COMPLETION_MISSING_OUTPUTS = "completion_missing_outputs"
    SPEAKER_TRUTH_BLOCKED = "speaker_truth_blocked"
    WORKSPACE_DISCOVERY_REQUIRED = "WORKSPACE_DISCOVERY_REQUIRED"
    APPROVAL_NOT_CREATED_PROMPT_CONTEXT_MISSING = "APPROVAL_NOT_CREATED_PROMPT_CONTEXT_MISSING"
    APPROVAL_NOT_CREATED_WORKSPACE_NOT_RESOLVED = "APPROVAL_NOT_CREATED_WORKSPACE_NOT_RESOLVED"
    APPROVAL_NOT_CREATED_NO_ANALYSIS_REF = "APPROVAL_NOT_CREATED_NO_ANALYSIS_REF"
    APPROVAL_NOT_CREATED_NO_TARGET_FILES = "APPROVAL_NOT_CREATED_NO_TARGET_FILES"
    APPROVAL_NOT_CREATED_NO_EXECUTABLE_PLAN = "APPROVAL_NOT_CREATED_NO_EXECUTABLE_PLAN"
    APPROVAL_NOT_CREATED_NO_EXPECTED_OUTPUTS = "APPROVAL_NOT_CREATED_NO_EXPECTED_OUTPUTS"
    APPROVAL_NOT_CREATED_NO_VALIDATION_PLAN = "APPROVAL_NOT_CREATED_NO_VALIDATION_PLAN"
    PREVIEW_REJECTED_GENERIC_WRITE_ACTION = "PREVIEW_REJECTED_GENERIC_WRITE_ACTION"
    PREVIEW_REJECTED_NO_TARGET_FILES = "PREVIEW_REJECTED_NO_TARGET_FILES"
    PREVIEW_REJECTED_NO_EXECUTABLE_PLAN = "PREVIEW_REJECTED_NO_EXECUTABLE_PLAN"
    PREVIEW_REJECTED_NO_EXPECTED_OUTPUTS = "PREVIEW_REJECTED_NO_EXPECTED_OUTPUTS"
    PREVIEW_REJECTED_NO_VALIDATION_PLAN = "PREVIEW_REJECTED_NO_VALIDATION_PLAN"
    PREVIEW_REJECTED_NO_ROLLBACK_PLAN = "PREVIEW_REJECTED_NO_ROLLBACK_PLAN"
    PREVIEW_REJECTED_NO_CONTEXT_REF = "PREVIEW_REJECTED_NO_CONTEXT_REF"


class CanonicalPermission(str, Enum):
    ALLOWED = "allowed"
    ASK = "ask"
    DENIED = "denied"
    NEEDS_CLARIFICATION = "needs_clarification"
    INVALID = "invalid"
    EXPIRED = "expired"
    STALE = "stale"


class PreviewKind(str, Enum):
    NONE = "none"
    PLAN_ONLY = "plan_only_preview"
    EXECUTABLE = "executable_task_preview"


class CanonicalIntentDecision(AIpinhoModel):
    intent_type: str = "conversation"
    operation_type: str = "conversation"
    requires_task: bool = False
    side_effect_requested: bool = False
    readonly: bool = False
    source_channel: str = "unknown"
    negative_constraints: dict[str, bool] = Field(default_factory=dict)
    confidence: float = 1.0
    evidence: list[str] = Field(default_factory=list)
    semantic_intent_graph: SemanticIntentGraph = Field(default_factory=SemanticIntentGraph)


class CanonicalOperationContract(AIpinhoModel):
    operation_id: str = Field(default_factory=lambda: f"op_{uuid4().hex}")
    session_id: str | None = None
    source_channel: str = "unknown"
    intent_type: str = "conversation"
    operation_type: str = "conversation"
    contract_type: str = "conversation"
    runtime_profile: str = "conversation"
    requested_actions: list[str] = Field(default_factory=list)
    target_paths: list[str] = Field(default_factory=list)
    workspace_path: str | None = None
    risk_level: str = "low"
    trace: list[dict[str, Any]] = Field(default_factory=list)


class CanonicalPolicyDecision(AIpinhoModel):
    permission: CanonicalPermission = CanonicalPermission.ALLOWED
    allowed_actions: list[str] = Field(default_factory=list)
    ask_actions: list[str] = Field(default_factory=list)
    denied_actions: list[str] = Field(default_factory=list)
    reason_code: GovernanceLifecycleReasonCode = GovernanceLifecycleReasonCode.NONE
    reason: str = ""
    source: str = "canonical_policy"
    requires_approval: bool = False
    trace: list[dict[str, Any]] = Field(default_factory=list)


class CanonicalExecutionPlan(AIpinhoModel):
    preview_kind: PreviewKind = PreviewKind.NONE
    executable: bool = False
    executable_plan_ref: str | None = None
    plan_kind: str | None = None
    expected_outputs: list[str] = Field(default_factory=list)
    target_paths: list[str] = Field(default_factory=list)
    blocked_reason: GovernanceLifecycleReasonCode = GovernanceLifecycleReasonCode.NONE
    trace: list[dict[str, Any]] = Field(default_factory=list)


class ContextGateDecision(AIpinhoModel):
    status: str = "ready"
    can_create_write_approval: bool = True
    reason_code: GovernanceLifecycleReasonCode = GovernanceLifecycleReasonCode.NONE
    source_message_id: str | None = None
    context_ref: str | None = None
    workspace_snapshot_ref: str | None = None
    discovery_ref: str | None = None
    analysis_ref: str | None = None
    missing_requirements: list[str] = Field(default_factory=list)
    trace: list[dict[str, Any]] = Field(default_factory=list)


class PreviewQualityDecision(AIpinhoModel):
    status: str = "ready"
    can_create_approval: bool = True
    reason_code: GovernanceLifecycleReasonCode = GovernanceLifecycleReasonCode.NONE
    missing_requirements: list[str] = Field(default_factory=list)
    trace: list[dict[str, Any]] = Field(default_factory=list)


class CanonicalApprovalGate(AIpinhoModel):
    required: bool = False
    can_create_approval: bool = False
    approval_id: str | None = None
    preview_id: str | None = None
    draft_id: str | None = None
    status: str = "not_required"
    reason_code: GovernanceLifecycleReasonCode = GovernanceLifecycleReasonCode.NONE
    trace: list[dict[str, Any]] = Field(default_factory=list)


class CanonicalValidationVerdict(AIpinhoModel):
    status: str = "not_run"
    safe_to_continue: bool = False
    missing_outputs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    reason_code: GovernanceLifecycleReasonCode = GovernanceLifecycleReasonCode.NONE


class CanonicalCompletionVerdict(AIpinhoModel):
    status: str = "not_run"
    safe_to_report_success: bool = False
    expected_outputs: list[str] = Field(default_factory=list)
    fulfilled_outputs: list[str] = Field(default_factory=list)
    missing_outputs: list[str] = Field(default_factory=list)
    reason_code: GovernanceLifecycleReasonCode = GovernanceLifecycleReasonCode.NONE


class CanonicalSpeakerTruth(AIpinhoModel):
    can_claim_success: bool = False
    message_status: str = "neutral"
    required_disclosures: list[str] = Field(default_factory=list)
    forbidden_claims: list[str] = Field(default_factory=list)
    reason_code: GovernanceLifecycleReasonCode = GovernanceLifecycleReasonCode.NONE


class GovernanceLifecycleSnapshot(AIpinhoModel):
    lifecycle_id: str = Field(default_factory=lambda: f"life_{uuid4().hex}")
    state: GovernanceLifecycleState = GovernanceLifecycleState.INTAKE
    reason_code: GovernanceLifecycleReasonCode = GovernanceLifecycleReasonCode.NONE
    intent: CanonicalIntentDecision = Field(default_factory=CanonicalIntentDecision)
    operation_contract: CanonicalOperationContract = Field(default_factory=CanonicalOperationContract)
    policy: CanonicalPolicyDecision = Field(default_factory=CanonicalPolicyDecision)
    context_gate: ContextGateDecision = Field(default_factory=ContextGateDecision)
    execution_plan: CanonicalExecutionPlan = Field(default_factory=CanonicalExecutionPlan)
    preview_quality: PreviewQualityDecision = Field(default_factory=PreviewQualityDecision)
    approval_gate: CanonicalApprovalGate = Field(default_factory=CanonicalApprovalGate)
    validation: CanonicalValidationVerdict = Field(default_factory=CanonicalValidationVerdict)
    completion: CanonicalCompletionVerdict = Field(default_factory=CanonicalCompletionVerdict)
    speaker_truth: CanonicalSpeakerTruth = Field(default_factory=CanonicalSpeakerTruth)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    task_run_id: str | None = None
    warnings: list[str] = Field(default_factory=list)
    trace: list[dict[str, Any]] = Field(default_factory=list)

    @property
    def status(self) -> str:
        return self.state.value
