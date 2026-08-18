from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def prefixed_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class MaintenanceScope(AIpinhoModel):
    task_id: str | None = None
    trace_id: str | None = None
    event_id: str | None = None
    session_id: str | None = None
    skill_trace_id: str | None = None
    context_bundle_id: str | None = None


class DiagnosisEvidence(AIpinhoModel):
    evidence_id: str = Field(default_factory=lambda: prefixed_id("maintenance_evidence"))
    source_type: str
    source_id: str
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0
    event_ref: str | None = None
    trace_ref: str | None = None
    raw_ref: str | None = None
    sanitized: bool = True


class AnomalySignal(AIpinhoModel):
    signal_id: str = Field(default_factory=lambda: prefixed_id("maintenance_signal"))
    signal_type: str
    source_ref: str
    severity: str = "info"
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now_iso)


class MaintenanceRequest(AIpinhoModel):
    request_id: str = Field(default_factory=lambda: prefixed_id("maintenance_request"))
    mode: str = "diagnose"
    scope: MaintenanceScope = Field(default_factory=MaintenanceScope)
    evidence: list[DiagnosisEvidence] = Field(default_factory=list)
    signals: dict[str, Any] = Field(default_factory=dict)
    reason: str = ""
    requested_by: str = "backend"


class DiagnosisRequest(MaintenanceRequest):
    mode: str = "diagnose"


class InvariantDefinition(AIpinhoModel):
    invariant_id: str
    severity: str
    description: str
    signals: list[str] = Field(default_factory=list)
    violation_if: dict[str, Any] = Field(default_factory=dict)
    recommended_action: str = "inspect_and_propose"


class InvariantEvidence(AIpinhoModel):
    invariant_id: str
    matched_conditions: dict[str, Any] = Field(default_factory=dict)
    source_refs: list[str] = Field(default_factory=list)


class InvariantViolation(AIpinhoModel):
    violation_id: str = Field(default_factory=lambda: prefixed_id("invariant_violation"))
    invariant_id: str
    severity: str
    description: str
    evidence: InvariantEvidence
    recommended_action: str
    created_at: str = Field(default_factory=utc_now_iso)


class InvariantCheckRequest(AIpinhoModel):
    request_id: str = Field(default_factory=lambda: prefixed_id("invariant_check"))
    signals: dict[str, Any] = Field(default_factory=dict)
    invariant_ids: list[str] = Field(default_factory=list)
    scope: MaintenanceScope = Field(default_factory=MaintenanceScope)


class InvariantCheckResult(AIpinhoModel):
    check_id: str = Field(default_factory=lambda: prefixed_id("invariant_result"))
    status: str
    checked_invariants: list[str] = Field(default_factory=list)
    violations: list[InvariantViolation] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)


class DiagnosisFinding(AIpinhoModel):
    finding_id: str = Field(default_factory=lambda: prefixed_id("diagnosis_finding"))
    title: str
    summary: str
    severity: str
    evidence_refs: list[str] = Field(default_factory=list)
    invariant_id: str | None = None
    fact_or_hypothesis: str = "fact"


class DiagnosisConfidence(AIpinhoModel):
    level: str
    score: float
    reasons: list[str] = Field(default_factory=list)


class DiagnosisHypothesis(AIpinhoModel):
    hypothesis_id: str = Field(default_factory=lambda: prefixed_id("diagnosis_hypothesis"))
    summary: str
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: DiagnosisConfidence


class RootCauseCandidate(AIpinhoModel):
    root_cause_id: str = Field(default_factory=lambda: prefixed_id("root_cause"))
    summary: str
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: DiagnosisConfidence


class DiagnosisResult(AIpinhoModel):
    diagnosis_id: str = Field(default_factory=lambda: prefixed_id("diagnosis"))
    run_id: str
    status: str
    findings: list[DiagnosisFinding] = Field(default_factory=list)
    evidence: list[DiagnosisEvidence] = Field(default_factory=list)
    anomalies: list[AnomalySignal] = Field(default_factory=list)
    invariant_result: InvariantCheckResult | None = None
    root_causes: list[RootCauseCandidate] = Field(default_factory=list)
    confidence: DiagnosisConfidence
    context_bundle_id: str | None = None
    context_trace_id: str | None = None
    created_at: str = Field(default_factory=utc_now_iso)


class MaintenanceTrace(AIpinhoModel):
    trace_id: str = Field(default_factory=lambda: prefixed_id("maintenance_trace"))
    run_id: str
    steps: list[dict[str, Any]] = Field(default_factory=list)
    event_ids: list[str] = Field(default_factory=list)
    context_bundle_id: str | None = None
    context_trace_id: str | None = None
    created_at: str = Field(default_factory=utc_now_iso)


class MaintenanceRun(AIpinhoModel):
    run_id: str = Field(default_factory=lambda: prefixed_id("maintenance_run"))
    request_id: str
    mode: str
    status: str = "created"
    scope: MaintenanceScope = Field(default_factory=MaintenanceScope)
    diagnosis: DiagnosisResult | None = None
    trace_id: str | None = None
    violations: list[InvariantViolation] = Field(default_factory=list)
    side_effects_performed: bool = False
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)


class MaintenanceResult(AIpinhoModel):
    status: str
    run: MaintenanceRun | None = None
    reasons: list[str] = Field(default_factory=list)


class MaintenanceAudit(AIpinhoModel):
    audit_id: str = Field(default_factory=lambda: prefixed_id("maintenance_audit"))
    action: str
    allowed: bool
    reasons: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now_iso)


class MaintenanceEvent(AIpinhoModel):
    event_type: str
    run_id: str | None = None
    human_summary: str
    technical_summary: str
    severity: str = "info"
    status: str = "created"


class RepairStep(AIpinhoModel):
    step_id: str = Field(default_factory=lambda: prefixed_id("repair_step"))
    action: str
    target: str | None = None
    description: str
    side_effect: bool = False


class RepairRisk(AIpinhoModel):
    level: str
    reasons: list[str] = Field(default_factory=list)
    approval_required: bool = False


class RepairValidationPlan(AIpinhoModel):
    plan_id: str = Field(default_factory=lambda: prefixed_id("validation_plan"))
    checks: list[str] = Field(default_factory=list)
    execution_performed: bool = False


class RepairPlan(AIpinhoModel):
    steps: list[RepairStep] = Field(default_factory=list)
    validation: RepairValidationPlan
    rollback_required: bool = False


class RepairProposalRequest(AIpinhoModel):
    diagnosis_run_id: str
    repair_type: str
    summary: str
    affected_targets: list[str] = Field(default_factory=list)
    proposed_steps: list[str] = Field(default_factory=list)
    validation_checks: list[str] = Field(default_factory=list)
    risk_signals: list[str] = Field(default_factory=list)


class RepairProposal(AIpinhoModel):
    proposal_id: str = Field(default_factory=lambda: prefixed_id("repair_proposal"))
    diagnosis_run_id: str
    repair_type: str
    status: str = "proposed"
    summary: str
    evidence_refs: list[str] = Field(default_factory=list)
    affected_targets: list[str] = Field(default_factory=list)
    plan: RepairPlan
    risk: RepairRisk
    approval_required: bool = False
    execution_performed: bool = False
    created_at: str = Field(default_factory=utc_now_iso)


class RepairPreview(AIpinhoModel):
    preview_id: str = Field(default_factory=lambda: prefixed_id("repair_preview"))
    proposal_id: str
    preview_type: str
    status: str = "preview_only"
    summary: str
    changes: list[dict[str, Any]] = Field(default_factory=list)
    write_performed: bool = False


class MaintenancePatchPreview(RepairPreview):
    preview_type: str = "patch_preview"
    delegated_to: str = "patch_planning_pipeline"
    diff_proposal_ref: str | None = None
    apply_performed: bool = False


class MaintenanceConfigChangePreview(RepairPreview):
    preview_type: str = "config_preview"


class MaintenanceValidationRecommendation(AIpinhoModel):
    recommendation_id: str = Field(default_factory=lambda: prefixed_id("maintenance_validation"))
    proposal_id: str
    checks: list[str] = Field(default_factory=list)
    rationale: str
    execution_performed: bool = False


class MaintenanceRollbackPlan(AIpinhoModel):
    rollback_id: str = Field(default_factory=lambda: prefixed_id("maintenance_rollback"))
    proposal_id: str
    steps: list[str] = Field(default_factory=list)
    execution_performed: bool = False


class RepairApprovalRequest(AIpinhoModel):
    approval_required: bool
    reason: str
    requested_action: str


class RepairHandoff(AIpinhoModel):
    handoff_id: str = Field(default_factory=lambda: prefixed_id("repair_handoff"))
    proposal_id: str
    target_owner: str
    status: str = "pending_approval"
    approval: RepairApprovalRequest
    execution_performed: bool = False


class RepairRejectionReason(AIpinhoModel):
    code: str
    human_reason: str


class MaintenanceLessonCandidate(AIpinhoModel):
    candidate_id: str = Field(default_factory=lambda: prefixed_id("maintenance_lesson"))
    run_id: str
    proposal_id: str | None = None
    problem: str
    cause: str
    evidence_refs: list[str]
    proposed_solution: str
    expected_result: str
    scope: str
    confidence: float
    status: str = "candidate"
    memory_mutation_performed: bool = False
    created_at: str = Field(default_factory=utc_now_iso)


class MaintenanceLessonCandidateRequest(AIpinhoModel):
    run_id: str
    proposal_id: str | None = None
    problem: str
    cause: str
    evidence_refs: list[str]
    proposed_solution: str
    expected_result: str
    scope: str
    confidence: float


class MaintenanceStatus(AIpinhoModel):
    status: str = "ok"
    enabled: bool = True
    mode: str = "supervised_autocure"
    supervised_autocure_enabled: bool = True
    autonomous_apply: bool = False
    diagnose_mode_enabled: bool = True
    repair_proposal_enabled: bool = True
    patch_preview_enabled: bool = True
    config_preview_enabled: bool = True
    validation_plan_enabled: bool = True
    rollback_plan_enabled: bool = True
    lesson_candidate_enabled: bool = True
    direct_patch_apply_enabled: bool = False
    direct_shell_enabled: bool = False
    direct_git_enabled: bool = False
    direct_policy_write_enabled: bool = False
    direct_memory_write_enabled: bool = False
    invariant_count: int = 0
    warnings: list[str] = Field(default_factory=list)


class HealthSignal(AnomalySignal):
    signal_type: str = "health"


class PolicyConflictSignal(AnomalySignal):
    signal_type: str = "policy_conflict"


class ContextDriftSignal(AnomalySignal):
    signal_type: str = "context_drift"


class SkillFailureSignal(AnomalySignal):
    signal_type: str = "skill_failure"


class RagStalenessSignal(AnomalySignal):
    signal_type: str = "rag_staleness"


class SpeakerTruthViolationSignal(AnomalySignal):
    signal_type: str = "speaker_truth_violation"


class ModelSelectionViolationSignal(AnomalySignal):
    signal_type: str = "model_selection_violation"


class EventContractViolationSignal(AnomalySignal):
    signal_type: str = "event_contract_violation"
