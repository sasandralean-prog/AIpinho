from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


ProjectProfileStatus = Literal["active", "draft", "stale", "invalid", "archived", "needs_review"]
WorkspaceRole = Literal[
    "source_readonly",
    "target_mutable",
    "artifacts",
    "reports",
    "logs",
    "backups",
    "temp",
    "generated",
    "protected",
    "forbidden",
]
StackKind = Literal[
    "android_gradle",
    "kotlin_android",
    "python",
    "node",
    "fastapi",
    "desktop_launcher",
    "mixed",
    "unknown",
]
CommandCategory = Literal["build", "test", "lint", "format", "smoke", "doctor", "package", "validate", "inspect", "custom"]
RiskLevel = Literal["low", "medium", "high", "critical"]
ValidationFailurePolicy = Literal[
    "block_completion",
    "allow_completed_with_warnings",
    "require_human_review",
    "create_self_healing_candidate",
]


class WorkspaceProfile(AIpinhoModel):
    workspace_id: str
    project_id: str
    role: WorkspaceRole
    path: str
    display_name: str | None = None
    access_policy: str = "policy_decides"
    write_policy: str = "policy_decides"
    shell_policy: str = "policy_decides"
    exists: bool = False
    last_seen_at: str | None = None
    validation_status: str = "unknown"
    protected_paths: list[str] = Field(default_factory=list)
    forbidden_paths: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class CommandProfile(AIpinhoModel):
    command_id: str
    project_id: str
    label: str
    command: list[str]
    working_directory_role: WorkspaceRole = "target_mutable"
    category: CommandCategory = "custom"
    risk_level: RiskLevel = "medium"
    requires_approval: bool = False
    allowed_execution_modes: list[str] = Field(default_factory=lambda: ["governed_autorun", "manual"])
    timeout_seconds: int = 300
    expected_outputs: list[str] = Field(default_factory=list)
    success_patterns: list[str] = Field(default_factory=list)
    failure_patterns: list[str] = Field(default_factory=list)
    redaction_required: bool = True
    evidence_refs: list[str] = Field(default_factory=list)


class ValidationProfile(AIpinhoModel):
    validation_profile_id: str
    project_id: str
    default_validation_sequence: list[str] = Field(default_factory=list)
    quick_validation_sequence: list[str] = Field(default_factory=list)
    full_validation_sequence: list[str] = Field(default_factory=list)
    smoke_validation_sequence: list[str] = Field(default_factory=list)
    file_existence_checks: list[str] = Field(default_factory=list)
    artifact_checks: list[str] = Field(default_factory=list)
    report_checks: list[str] = Field(default_factory=list)
    command_profiles: list[str] = Field(default_factory=list)
    required_evidence: list[str] = Field(default_factory=list)
    validation_timeout_seconds: int = 900
    validation_failure_policy: ValidationFailurePolicy = "block_completion"


class ProjectProfile(AIpinhoModel):
    project_id: str = Field(default_factory=lambda: f"project_{uuid4().hex}")
    display_name: str
    slug: str
    description: str = ""
    owner_label: str | None = None
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    last_validated_at: str | None = None
    profile_version: int = 1
    profile_status: ProjectProfileStatus = "draft"
    root_ref: str
    source_readonly_workspace_id: str | None = None
    target_mutable_workspace_id: str | None = None
    protected_paths: list[str] = Field(default_factory=list)
    forbidden_paths: list[str] = Field(default_factory=list)
    stack: StackKind = "unknown"
    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    package_managers: list[str] = Field(default_factory=list)
    build_system: str | None = None
    test_system: str | None = None
    validation_profile_id: str | None = None
    command_profiles: list[CommandProfile] = Field(default_factory=list)
    workspace_profiles: list[WorkspaceProfile] = Field(default_factory=list)
    validation_profiles: list[ValidationProfile] = Field(default_factory=list)
    policy_profile_id: str | None = None
    memory_namespace: str | None = None
    artifact_namespace: str | None = None
    report_namespace: str | None = None
    default_agent_preferences: dict[str, Any] = Field(default_factory=dict)
    known_risks: list[str] = Field(default_factory=list)
    accepted_decisions: list[str] = Field(default_factory=list)
    known_commands: list[str] = Field(default_factory=list)
    environment_requirements: list[str] = Field(default_factory=list)
    redaction_rules: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class ProjectProfileCandidate(AIpinhoModel):
    candidate_id: str = Field(default_factory=lambda: f"profile_candidate_{uuid4().hex}")
    detected_stack: StackKind = "unknown"
    confidence: float = 0.0
    root_path: str
    detected_files: list[str] = Field(default_factory=list)
    suggested_workspaces: list[WorkspaceProfile] = Field(default_factory=list)
    suggested_commands: list[CommandProfile] = Field(default_factory=list)
    suggested_validation_profile: ValidationProfile | None = None
    risks: list[str] = Field(default_factory=list)
    missing_info: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class ProjectProfileCreateRequest(AIpinhoModel):
    profile: ProjectProfile
    allow_needs_review: bool = True


class ProjectProfileUpdateRequest(AIpinhoModel):
    display_name: str | None = None
    description: str | None = None
    profile_status: ProjectProfileStatus | None = None
    known_risks: list[str] | None = None
    accepted_decisions: list[str] | None = None
    metadata_sanitized: dict[str, Any] | None = None


class ProjectProfileDetectionRequest(AIpinhoModel):
    root_path: str
    display_name: str | None = None
    create_draft: bool = False


class ProjectProfileSelectionRequest(AIpinhoModel):
    agent_id: str | None = None
    session_id: str | None = None
    project_id: str


class ProjectProfileValidationResult(AIpinhoModel):
    project_id: str
    status: str
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)

