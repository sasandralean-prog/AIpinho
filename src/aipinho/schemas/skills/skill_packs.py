from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import Field, model_validator

from aipinho.schemas.common.base import AIpinhoModel


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


SkillPackStatus = Literal["active", "experimental", "deprecated", "disabled", "invalid", "archived"]
SkillPackCategory = Literal[
    "android",
    "python",
    "docs",
    "artifact",
    "sandbox",
    "debugging",
    "ux",
    "workspace",
    "promotion",
    "validation",
    "release",
]
SkillPackRiskLevel = Literal["low", "medium", "high", "critical"]
SkillPackAgent = Literal["aipinho", "lucio", "codex", "gemini", "autopilot"]
SkillPackExecutionMode = Literal[
    "safe_chat",
    "assisted_execution",
    "sandbox_play",
    "sandbox_project_generation",
    "sandbox_autopilot",
    "promotion_plan",
    "promotion_apply",
    "project_readonly_analysis",
    "governed_autorun",
]
SkillPackExecutionStatus = Literal[
    "queued",
    "running",
    "completed",
    "completed_with_warnings",
    "blocked",
    "failed",
    "validation_failed",
    "cancelled",
]


class SkillPackExample(AIpinhoModel):
    label: str
    prompt: str = ""
    expected_pack_selection: list[str] = Field(default_factory=list)


class SkillPackManifest(AIpinhoModel):
    skill_pack_id: str
    display_name: str
    slug: str
    version: str
    status: SkillPackStatus = "active"
    category: SkillPackCategory
    description: str
    included_skills: list[str] = Field(default_factory=list)
    required_capabilities: list[str] = Field(default_factory=list)
    optional_capabilities: list[str] = Field(default_factory=list)
    supported_agents: list[SkillPackAgent] = Field(default_factory=lambda: ["aipinho", "autopilot"])
    supported_project_stacks: list[str] = Field(default_factory=lambda: ["mixed", "unknown"])
    supported_execution_modes: list[SkillPackExecutionMode] = Field(default_factory=lambda: ["assisted_execution"])
    risk_level: SkillPackRiskLevel = "medium"
    policy_profile: str = "default"
    validation_profile: str | None = None
    artifact_policy: str = "default"
    memory_policy: str = "none"
    dashboard_visible: bool = True
    debugger_trace_required: bool = True
    docs_ref: str
    tests_ref: str
    examples: list[SkillPackExample] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    evidence_refs: list[str] = Field(default_factory=list)
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_boundaries(self) -> "SkillPackManifest":
        if not self.included_skills:
            raise ValueError("skill_pack_requires_included_skills")
        if not self.supported_agents:
            raise ValueError("skill_pack_requires_supported_agents")
        if not self.supported_execution_modes:
            raise ValueError("skill_pack_requires_execution_modes")
        if self.risk_level in {"high", "critical"} and not self.validation_profile:
            raise ValueError("high_risk_pack_requires_validation_profile")
        return self


class SkillPackValidationResult(AIpinhoModel):
    skill_pack_id: str | None = None
    valid: bool
    status: str
    reason_codes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    safe_remediation: list[str] = Field(default_factory=list)
    manifest: SkillPackManifest | None = None
    health_status: str = "unknown"


class SkillPackHealth(AIpinhoModel):
    skill_pack_id: str
    status: str
    health_status: str
    validation: SkillPackValidationResult
    skill_count: int = 0
    warnings: list[str] = Field(default_factory=list)


class SkillPackRegistryStatus(AIpinhoModel):
    status: str
    pack_count: int = 0
    active_count: int = 0
    invalid_count: int = 0
    deprecated_count: int = 0
    experimental_count: int = 0
    root: str
    skill_packs_enabled: bool = True


class SkillPackSelectionRequest(AIpinhoModel):
    user_goal: str = ""
    agent_id: str = "autopilot"
    project_stack: str | None = None
    execution_mode: str | None = None
    requested_capabilities: list[str] = Field(default_factory=list)
    risk_ceiling: str = "critical"
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class SkillPackSelectionCandidate(AIpinhoModel):
    skill_pack_id: str
    score: float
    reasons: list[str] = Field(default_factory=list)
    selected_skills: list[str] = Field(default_factory=list)
    risk_level: str = "medium"


class SkillPackSelectionResult(AIpinhoModel):
    status: str
    candidates: list[SkillPackSelectionCandidate] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class SkillPackExecutionRequest(AIpinhoModel):
    skill_pack_execution_id: str = Field(default_factory=lambda: f"skill_pack_exec_{uuid4().hex}")
    skill_pack_id: str
    skill_pack_version: str | None = None
    requested_skill_id: str | None = None
    requesting_agent_id: str
    session_id: str
    run_id: str | None = None
    user_goal: str = ""
    project_profile_id: str | None = None
    sandbox_task_id: str | None = None
    sandbox_workspace_id: str | None = None
    workspace_id: str | None = None
    autopilot_run_id: str | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    expected_outputs: list[str] = Field(default_factory=list)
    execution_mode: str = "governed_autorun"
    requested_capabilities: list[str] = Field(default_factory=list)
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class SkillPackExecutionResult(AIpinhoModel):
    skill_pack_execution_id: str
    skill_pack_id: str
    skill_pack_version: str
    status: SkillPackExecutionStatus
    selected_skills: list[str] = Field(default_factory=list)
    skill_execution_ids: list[str] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)
    reports: list[str] = Field(default_factory=list)
    validation_ids: list[str] = Field(default_factory=list)
    policy_decision_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    started_at: str = Field(default_factory=utc_now_iso)
    completed_at: str | None = None
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)
