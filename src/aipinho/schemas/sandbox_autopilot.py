from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso
from aipinho.schemas.project_generation import ProjectGenerationResult, ProjectType


SandboxAutopilotStatus = Literal[
    "routed",
    "completed",
    "completed_with_warnings",
    "blocked",
    "failed",
    "validation_failed",
    "artifact_failed",
]


class SandboxAutopilotRequest(AIpinhoModel):
    autopilot_run_id: str = Field(default_factory=lambda: f"sandbox_autopilot_{uuid4().hex}")
    session_id: str | None = None
    requesting_agent_id: str = "aipinho"
    user_goal: str
    sandbox_workspace_id: str = "sandbox_ws_default"
    project_name: str | None = None
    project_type: ProjectType = "unknown"
    output_zip_name: str | None = None
    requested_assets: list[str] = Field(default_factory=list)
    requested_features: list[str] = Field(default_factory=list)
    dry_run: bool = False
    allow_correction_loops: bool = True
    max_correction_loops: int = 2
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class SandboxAutopilotRouteDecision(AIpinhoModel):
    autopilot_run_id: str
    status: str
    mode: str = "sandbox_autopilot"
    route_type: str
    recommended_skills: list[str] = Field(default_factory=list)
    project_type: ProjectType = "unknown"
    project_name: str | None = None
    use_sandbox: bool = True
    requires_workspace: bool = False
    safe_alternative: str | None = None
    risk_level: str = "low"
    reasons: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class SandboxAutopilotResult(AIpinhoModel):
    autopilot_run_id: str
    status: SandboxAutopilotStatus
    mode: str = "sandbox_autopilot"
    route_decision: SandboxAutopilotRouteDecision
    project_generation: ProjectGenerationResult | None = None
    artifact_ids: list[str] = Field(default_factory=list)
    zip_artifact_id: str | None = None
    download_endpoint: str | None = None
    requires_token: bool = True
    validation_status: str | None = None
    correction_loops: list[dict[str, Any]] = Field(default_factory=list)
    final_answer_sanitized: str
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    started_at: str = Field(default_factory=utc_now_iso)
    completed_at: str | None = None
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)

