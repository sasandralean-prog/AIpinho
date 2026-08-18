from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


ProjectType = Literal[
    "android_kotlin",
    "android_kotlin_app",
    "python_cli",
    "python_simple_app",
    "python_fastapi",
    "static_web",
    "docs_pack",
    "markdown_docs",
    "mobile_component_demo",
    "launcher_tool_demo",
    "generic_files",
    "unknown",
]
ValidationLevel = Literal["structural", "syntax", "build_if_available", "full_if_available"]
ProjectGenerationStatus = Literal[
    "queued",
    "running",
    "validation_failed",
    "artifact_failed",
    "completed",
    "completed_with_warnings",
    "blocked",
    "failed",
    "cancelled",
    "timed_out",
]


class ProjectGenerationRequest(AIpinhoModel):
    project_generation_id: str = Field(default_factory=lambda: f"project_generation_{uuid4().hex}")
    sandbox_task_id: str | None = None
    sandbox_workspace_id: str = "sandbox_ws_default"
    session_id: str | None = None
    requesting_agent_id: str = "aipinho"
    user_goal: str
    project_name: str | None = None
    project_type: ProjectType = "unknown"
    target_platform: str | None = None
    language: str | None = None
    framework: str | None = None
    requested_features: list[str] = Field(default_factory=list)
    requested_assets: list[str] = Field(default_factory=list)
    output_zip_name: str | None = None
    validation_level: ValidationLevel = "structural"
    allow_placeholders: bool = True
    build_if_possible: bool = True
    artifact_requested: bool = True
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class ProjectGenerationResult(AIpinhoModel):
    project_generation_id: str
    sandbox_task_id: str
    sandbox_workspace_id: str
    status: ProjectGenerationStatus
    project_root: str
    project_name: str
    project_type: ProjectType
    files_created: list[str] = Field(default_factory=list)
    files_modified: list[str] = Field(default_factory=list)
    assets_created: list[str] = Field(default_factory=list)
    validation_ids: list[str] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    zip_artifact_id: str | None = None
    report_artifact_id: str | None = None
    download_endpoint: str | None = None
    requires_token: bool = True
    final_answer_sanitized: str
    evidence_refs: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    started_at: str = Field(default_factory=utc_now_iso)
    completed_at: str | None = None
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class ProjectGenerationRouteDecision(AIpinhoModel):
    status: str
    route_type: str
    project_type: ProjectType = "unknown"
    project_name: str | None = None
    requires_workspace: bool = False
    use_sandbox: bool = False
    safe_alternative: str | None = None
    reasons: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
