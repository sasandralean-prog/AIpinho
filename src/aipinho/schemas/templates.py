from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


TemplateStatus = Literal["active", "experimental", "deprecated", "disabled", "invalid"]
TemplateCategory = Literal[
    "android",
    "android_game",
    "python",
    "web",
    "docs",
    "mobile_component",
    "launcher_tool",
    "generic",
]
TemplateExecutionStatus = Literal[
    "queued",
    "running",
    "validation_failed",
    "artifact_failed",
    "completed",
    "completed_with_warnings",
    "blocked",
    "failed",
    "cancelled",
]


class TemplateManifest(AIpinhoModel):
    template_id: str
    display_name: str
    slug: str
    version: str
    status: TemplateStatus = "active"
    category: TemplateCategory
    description: str
    supported_project_types: list[str] = Field(default_factory=list)
    supported_languages: list[str] = Field(default_factory=list)
    supported_platforms: list[str] = Field(default_factory=list)
    generator_key: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    required_files: list[str] = Field(default_factory=list)
    optional_files: list[str] = Field(default_factory=list)
    generated_assets: list[str] = Field(default_factory=list)
    validation_profile: dict[str, Any] = Field(default_factory=dict)
    build_profile: dict[str, Any] = Field(default_factory=dict)
    artifact_policy: dict[str, Any] = Field(default_factory=dict)
    risk_level: str = "low"
    required_capabilities: list[str] = Field(default_factory=list)
    compatible_skills: list[str] = Field(default_factory=list)
    compatible_autopilot_modes: list[str] = Field(default_factory=list)
    docs_ref: str | None = None
    tests_ref: str | None = None
    examples: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    evidence_refs: list[str] = Field(default_factory=list)
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class TemplateRegistryStatus(AIpinhoModel):
    status: str
    templates_loaded: int
    active_templates: int
    invalid_templates: int
    version: str = "1"
    warnings: list[str] = Field(default_factory=list)


class TemplateExecutionRequest(AIpinhoModel):
    template_execution_id: str = Field(default_factory=lambda: f"template_exec_{uuid4().hex}")
    template_id: str
    template_version: str | None = None
    sandbox_task_id: str | None = None
    session_id: str | None = None
    requesting_agent_id: str = "aipinho"
    user_goal: str
    project_name: str
    output_directory: str | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    requested_assets: list[str] = Field(default_factory=list)
    output_zip_name: str | None = None
    validation_level: str = "structural"
    build_if_available: bool = True
    artifact_requested: bool = True
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class AssetManifest(AIpinhoModel):
    asset_id: str = Field(default_factory=lambda: f"asset_{uuid4().hex}")
    display_name: str
    filename: str
    asset_type: str
    format: str
    generated: bool = True
    source: str = "local_placeholder_generator"
    dimensions: dict[str, int] = Field(default_factory=dict)
    size_bytes: int = 0
    usage: str = "placeholder"
    template_id: str | None = None
    license_note: str = "Generated local placeholder. Replace before production if needed."
    evidence_refs: list[str] = Field(default_factory=list)
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class TemplateExecutionResult(AIpinhoModel):
    template_execution_id: str
    template_id: str
    template_version: str
    status: TemplateExecutionStatus
    project_root: str
    files_created: list[str] = Field(default_factory=list)
    files_modified: list[str] = Field(default_factory=list)
    assets_created: list[str] = Field(default_factory=list)
    asset_manifests: list[AssetManifest] = Field(default_factory=list)
    validation_ids: list[str] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    started_at: str = Field(default_factory=utc_now_iso)
    completed_at: str | None = None
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class TemplateExecutionBundle(AIpinhoModel):
    execution: TemplateExecutionResult
    files: dict[str, str] = Field(default_factory=dict)
