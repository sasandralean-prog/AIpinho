from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.roles.role_pass import RolePass
from aipinho.schemas.roles.role_pipeline_trace import RolePipelineTraceItem

RolePipelineRunStatus = Literal["preview", "completed", "partial", "failed", "rejected", "degraded", "needs_input"]


class RolePipelineRunRequest(AIpinhoModel):
    pipeline_id: str | None = None
    intent_map: dict[str, Any] = Field(default_factory=dict)
    policy_decision: dict[str, Any] = Field(default_factory=dict)
    task_draft: dict[str, Any] = Field(default_factory=dict)
    project_report: dict[str, Any] = Field(default_factory=dict)
    file_context_bundle: dict[str, Any] = Field(default_factory=dict)
    context_injection_plan_id: str | None = None
    context_injection_plan: dict[str, Any] = Field(default_factory=dict)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    user_message: str = ""
    session_id: str | None = None
    mode: Literal["preview", "run"] = "preview"
    include_trace: bool = False
    model_mode: Literal["deterministic", "stub", "manual_real"] = "stub"
    allow_real_inference: bool = False
    operator_confirmed: bool = False


class RolePipelineRun(AIpinhoModel):
    run_id: str = Field(default_factory=lambda: f"role_pipeline_run_{uuid4().hex}")
    pipeline_id: str
    status: RolePipelineRunStatus = "preview"
    input_summary: dict[str, Any] = Field(default_factory=dict)
    passes: list[RolePass] = Field(default_factory=list)
    final_output: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    trace: list[RolePipelineTraceItem] = Field(default_factory=list)
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished_at: str | None = None
    validation_summary: dict[str, Any] | None = None

    def finish(self, status: RolePipelineRunStatus) -> None:
        self.status = status
        self.finished_at = datetime.now(timezone.utc).isoformat()

