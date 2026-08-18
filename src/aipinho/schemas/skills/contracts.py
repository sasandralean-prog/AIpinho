from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import Field, model_validator

from aipinho.schemas.common.base import AIpinhoModel

SkillNamespace = str
SkillCategory = str
SkillRiskLevel = str
SkillStatus = str
SkillManifestStatus = Literal["draft", "active", "disabled", "deprecated", "invalid", "experimental", "archived"]
SkillManifestCategory = Literal[
    "analysis",
    "planning",
    "code_modification",
    "validation",
    "reporting",
    "artifact_generation",
    "project_onboarding",
    "debugging",
    "mobile_ux",
    "release",
    "cleanup",
    "self_healing",
    "multimodal_analysis",
]
SkillManifestRiskLevel = Literal["low", "medium", "high", "critical"]
SkillExecutionStatus = Literal[
    "queued",
    "running",
    "pending_approval",
    "blocked",
    "validation_failed",
    "failed",
    "completed",
    "completed_with_warnings",
    "cancelled",
    "timed_out",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class SkillCapabilityRequirement(AIpinhoModel):
    capability: str
    required: bool = True
    reason: str = ""


class SkillToolPermission(AIpinhoModel):
    tool_id: str
    allowed: bool = False
    call_modes: list[str] = Field(default_factory=lambda: ["preview_only"])
    reason: str = ""


class SkillContextRequirement(AIpinhoModel):
    purpose: str = "skill_execution_future"
    bundle_required: bool = True
    safe_for_prompt_required: bool = True


class SkillInputContract(AIpinhoModel):
    type: str = "object"
    required: list[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)
    additional_properties: bool = False


class SkillOutputContract(AIpinhoModel):
    type: str = "object"
    required: list[str] = Field(default_factory=lambda: ["summary"])
    properties: dict[str, Any] = Field(default_factory=lambda: {"summary": {"type": "string"}})
    additional_properties: bool = True


class SkillValidationRule(AIpinhoModel):
    rule_id: str
    description: str = ""
    required: bool = True


class SkillFallback(AIpinhoModel):
    mode: str = "block"
    target_skill_id: str | None = None
    human_message: str = "Skill indisponivel; nenhuma execucao foi realizada."


class SkillAntiTrigger(AIpinhoModel):
    signal: str
    reason: str


class SkillFailureMode(AIpinhoModel):
    code: str
    behavior: str = "block"
    human_message: str = ""


class SkillExample(AIpinhoModel):
    label: str
    input: dict[str, Any] = Field(default_factory=dict)
    expected_mode: str = "preview"


class SkillContract(AIpinhoModel):
    skill_id: str
    namespace: SkillNamespace
    category: SkillCategory
    display_name: str
    purpose: str
    when_to_use: list[str]
    when_not_to_use: list[str]
    input_contract: SkillInputContract
    output_contract: SkillOutputContract
    required_context_purpose: str
    required_capabilities: list[str]
    allowed_tools: list[str]
    forbidden_tools: list[str]
    risk_level: SkillRiskLevel
    approval_required: bool
    supports_preview: bool = True
    supports_dry_run: bool = True
    supports_real_execution: bool = False
    validation: list[SkillValidationRule]
    fallback: SkillFallback
    anti_triggers: list[SkillAntiTrigger]
    examples: list[SkillExample]
    failure_modes: list[SkillFailureMode]
    events_emitted: list[str]
    debugger_trace_policy: str = "sanitized"
    status: SkillStatus = "disabled"
    default_enabled: bool = False
    execution_mode: str = "preview_only"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_contract_boundaries(self) -> "SkillContract":
        if self.supports_real_execution:
            raise ValueError("skill_real_execution_not_supported")
        if self.risk_level in {"high", "critical"} and not self.approval_required:
            raise ValueError("high_risk_skill_requires_approval")
        if set(self.allowed_tools) & set(self.forbidden_tools):
            raise ValueError("tool_cannot_be_allowed_and_forbidden")
        if not self.required_context_purpose:
            raise ValueError("required_context_purpose_missing")
        return self


class SkillRegistryEntry(AIpinhoModel):
    skill_id: str
    status: str
    risk_level: str
    execution_mode: str
    contract_valid: bool = True


class SkillCatalog(AIpinhoModel):
    schema_version: int = 1
    skills: list[SkillContract] = Field(default_factory=list)


class SkillRouteRequest(AIpinhoModel):
    requested_skill_id: str | None = None
    category: str | None = None
    purpose: str | None = None
    context_purpose: str | None = None
    context_bundle_id: str | None = None
    granted_capabilities: list[str] = Field(default_factory=list)
    signals: list[str] = Field(default_factory=list)
    risk_ceiling: str = "critical"
    task_contract: dict[str, Any] = Field(default_factory=dict)


class SkillRouteCandidate(AIpinhoModel):
    skill_id: str
    score: float
    reasons: list[str] = Field(default_factory=list)
    approval_required: bool = False
    execution_mode: str = "preview_only"


class SkillRouteResult(AIpinhoModel):
    status: str
    candidates: list[SkillRouteCandidate] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    trace_id: str | None = None
    execution_started: bool = False


class SkillExecutionEnvelope(AIpinhoModel):
    envelope_id: str = Field(default_factory=lambda: f"skill_envelope_{uuid4().hex}")
    skill_id: str
    context_bundle_id: str
    granted_capabilities: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    denied_tools: list[str] = Field(default_factory=list)
    approval_required: bool = False
    side_effects_allowed: bool = False
    real_execution_allowed: bool = False
    task_contract_snapshot: dict[str, Any] = Field(default_factory=dict)


class SkillPreviewRequest(AIpinhoModel):
    skill_id: str
    context_bundle_id: str | None = None
    granted_capabilities: list[str] = Field(default_factory=list)
    requested_tools: list[str] = Field(default_factory=list)
    task_contract: dict[str, Any] = Field(default_factory=dict)
    signals: list[str] = Field(default_factory=list)
    approval_id: str | None = None


class SkillPreviewResult(AIpinhoModel):
    preview_id: str = Field(default_factory=lambda: f"skill_preview_{uuid4().hex}")
    status: str
    skill_id: str
    execution_mode: str = "preview_only"
    envelope: SkillExecutionEnvelope | None = None
    planned_steps: list[dict[str, Any]] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    approval_required: bool = False
    safe_to_execute: bool = False
    side_effects_performed: bool = False
    trace_id: str | None = None


class SkillDryRunRequest(SkillPreviewRequest):
    side_effects_allowed: bool = False


class SkillDryRunResult(AIpinhoModel):
    dry_run_id: str = Field(default_factory=lambda: f"skill_dry_run_{uuid4().hex}")
    status: str
    skill_id: str
    preview_id: str | None = None
    simulated_tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    simulated_output: dict[str, Any] = Field(default_factory=dict)
    output_valid: bool = False
    blocked_reasons: list[str] = Field(default_factory=list)
    side_effects_performed: bool = False
    safe_to_execute: bool = False
    trace_id: str | None = None


class SkillExecutionResult(AIpinhoModel):
    skill_execution_id: str = Field(default_factory=lambda: f"skill_exec_{uuid4().hex}")
    skill_id: str
    skill_version: str | None = None
    status: SkillExecutionStatus = "blocked"
    started_at: str = Field(default_factory=utc_now_iso)
    completed_at: str | None = None
    output: dict[str, Any] = Field(default_factory=dict)
    output_artifact_refs: list[str] = Field(default_factory=list)
    report_refs: list[str] = Field(default_factory=list)
    tool_invocation_ids: list[str] = Field(default_factory=list)
    policy_decision_ids: list[str] = Field(default_factory=list)
    validation_ids: list[str] = Field(default_factory=list)
    memory_candidate_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    real_execution_performed: bool = False
    blocked_reasons: list[str] = Field(default_factory=list)
    speaker_truth_status: str = "raw_hidden_by_default"
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class SkillCompositionPlan(AIpinhoModel):
    composition_id: str = Field(default_factory=lambda: f"skill_composition_{uuid4().hex}")
    status: str
    skill_ids: list[str] = Field(default_factory=list)
    steps: list[dict[str, Any]] = Field(default_factory=list)
    approval_required: bool = False
    real_execution_allowed: bool = False
    blocked_reasons: list[str] = Field(default_factory=list)


class SkillCompositionResult(AIpinhoModel):
    status: str
    plan: SkillCompositionPlan
    execution_started: bool = False


class SkillOutputValidationResult(AIpinhoModel):
    status: str
    skill_id: str
    accepted: bool
    missing_fields: list[str] = Field(default_factory=list)
    violations: list[str] = Field(default_factory=list)
    sanitized_output: dict[str, Any] = Field(default_factory=dict)


class SkillInstallRequest(AIpinhoModel):
    manifest: dict[str, Any]
    contract: dict[str, Any]
    dependencies: list[str] = Field(default_factory=list)
    source_uri: str | None = None


class SkillInstallPreview(AIpinhoModel):
    install_preview_id: str = Field(default_factory=lambda: f"skill_install_preview_{uuid4().hex}")
    status: str
    skill_id: str | None = None
    contract_valid: bool = False
    approval_required: bool = True
    files_written: bool = False
    dependencies_installed: bool = False
    blocked_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SkillInstallResult(AIpinhoModel):
    status: str = "preview_only"
    preview: SkillInstallPreview
    installed: bool = False


class SkillTraceStep(AIpinhoModel):
    stage: str
    decision: str
    reason: str
    details: dict[str, Any] = Field(default_factory=dict)


class SkillTrace(AIpinhoModel):
    trace_id: str = Field(default_factory=lambda: f"skill_trace_{uuid4().hex}")
    skill_id: str | None = None
    operation: str
    status: str
    steps: list[SkillTraceStep] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)


class SkillAudit(AIpinhoModel):
    audit_id: str = Field(default_factory=lambda: f"skill_audit_{uuid4().hex}")
    action: str
    skill_id: str | None = None
    allowed: bool
    reasons: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)


class SkillManifest(AIpinhoModel):
    skill_id: str
    display_name: str
    slug: str
    description: str
    version: str
    status: SkillManifestStatus = "draft"
    category: SkillManifestCategory
    owner: str = "aipinho"
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    min_aipinho_version: str | None = None
    compatible_agents: list[str] = Field(default_factory=list)
    compatible_project_stacks: list[str] = Field(default_factory=lambda: ["unknown", "mixed"])
    required_capabilities: list[str] = Field(default_factory=list)
    optional_capabilities: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    denied_tools: list[str] = Field(default_factory=list)
    input_schema: dict[str, Any] = Field(default_factory=lambda: {"type": "object"})
    output_schema: dict[str, Any] = Field(default_factory=lambda: {"type": "object"})
    side_effects: list[str] = Field(default_factory=list)
    workspace_policy: dict[str, Any] = Field(default_factory=dict)
    sandbox_required: bool = False
    sandbox_allowed: bool = False
    sandbox_side_effects: list[str] = Field(default_factory=list)
    command_policy: dict[str, Any] = Field(default_factory=dict)
    artifact_policy: dict[str, Any] = Field(default_factory=dict)
    memory_policy: dict[str, Any] = Field(default_factory=lambda: {"mode": "none"})
    validation_policy: dict[str, Any] = Field(default_factory=dict)
    speaker_truth_policy: dict[str, Any] = Field(default_factory=lambda: {"raw_hidden_by_default": True})
    risk_level: SkillManifestRiskLevel = "low"
    approval_policy: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = 300
    max_steps: int = 8
    examples: list[dict[str, Any]] = Field(default_factory=list)
    docs_ref: str | None = None
    tests_ref: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class SkillManifestValidationResult(AIpinhoModel):
    skill_id: str | None = None
    valid: bool
    status: str
    reason_codes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    safe_remediation: list[str] = Field(default_factory=list)
    manifest: SkillManifest | None = None


class SkillRegistryStatusV2(AIpinhoModel):
    status: str
    manifest_count: int = 0
    active_count: int = 0
    invalid_count: int = 0
    deprecated_count: int = 0
    experimental_count: int = 0
    root: str


class SkillExecutionRequest(AIpinhoModel):
    skill_execution_id: str = Field(default_factory=lambda: f"skill_exec_{uuid4().hex}")
    skill_id: str
    skill_version: str | None = None
    requesting_agent_id: str
    session_id: str
    run_id: str | None = None
    project_profile_id: str | None = None
    workspace_profile_id: str | None = None
    sandbox_workspace_id: str | None = None
    sandbox_task_id: str | None = None
    user_goal: str = ""
    inputs: dict[str, Any] = Field(default_factory=dict)
    artifact_refs: list[str] = Field(default_factory=list)
    context_refs: list[str] = Field(default_factory=list)
    execution_mode: str = "governed_autorun"
    requested_capabilities: list[str] = Field(default_factory=list)
    risk_override_request: str | None = None
    approval_context: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int | None = None
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class SkillHealth(AIpinhoModel):
    skill_id: str
    status: str
    validation: SkillManifestValidationResult
    last_execution_status: str | None = None
    warnings: list[str] = Field(default_factory=list)
