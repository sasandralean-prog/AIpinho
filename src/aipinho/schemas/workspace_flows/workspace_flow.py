from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.config_governance.workspace_permission import WorkspaceRegistryRole

WorkspaceFlowOperation = Literal[
    "copy_file",
    "move_file",
    "import_file",
    "download_to_staging",
    "apply_asset_to_project",
    "read_from_source_apply_to_target",
    "git_push",
    "delete_file",
]

WorkspaceFlowPolicy = Literal["allowed", "ask", "denied"]
WorkspaceFlowRisk = Literal["low", "medium", "high"]
WorkspaceFlowStatus = Literal["planned", "pending_approval", "approved", "running", "completed", "failed", "cancelled", "blocked"]
WorkspaceFlowStepStatus = Literal["pending", "approved", "running", "completed", "failed", "skipped"]


class WorkspaceFlowRule(AIpinhoModel):
    flow_id: str
    source_workspace_id: str
    target_workspace_id: str
    operation: WorkspaceFlowOperation
    source_policy: WorkspaceFlowPolicy
    target_policy: WorkspaceFlowPolicy
    requires_preview: bool = True
    requires_approval: bool = True
    allow_batch: bool = False
    risk_level: WorkspaceFlowRisk = "medium"
    enabled: bool = True
    created_at: str
    updated_at: str


class WorkspaceFlowEndpoint(AIpinhoModel):
    path: str
    workspace_id: str | None = None
    role: WorkspaceRegistryRole | None = None
    required_permissions: list[str] = Field(default_factory=list)


class WorkspaceFlowStep(AIpinhoModel):
    step_id: str
    operation: str
    source_path: str | None = None
    target_path: str | None = None
    command: str | None = None
    permission_decision: WorkspaceFlowPolicy = "allowed"
    requires_approval: bool = False
    approval_id: str | None = None
    status: WorkspaceFlowStepStatus = "pending"


class WorkspaceFlowPlan(AIpinhoModel):
    flow_plan_id: str
    run_id: str | None = None
    task_id: str | None = None
    operation: WorkspaceFlowOperation
    source: WorkspaceFlowEndpoint | None = None
    target: WorkspaceFlowEndpoint | None = None
    steps: list[WorkspaceFlowStep] = Field(default_factory=list)
    risk_level: WorkspaceFlowRisk = "medium"
    requires_approval: bool = True
    approval_id: str | None = None
    status: WorkspaceFlowStatus = "planned"
    reason_codes: list[str] = Field(default_factory=list)
    evidence_refs: list[dict[str, str]] = Field(default_factory=list)
    created_at: str
    updated_at: str


class WorkspaceFlowPlanRequest(AIpinhoModel):
    operation: WorkspaceFlowOperation
    source_path: str | None = None
    target_path: str | None = None
    source: WorkspaceFlowEndpoint | None = None
    target: WorkspaceFlowEndpoint | None = None
    requested_by: dict[str, object] = Field(default_factory=dict)
    run_id: str | None = None
    task_id: str | None = None
    command: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class WorkspaceFlowExecutionResult(AIpinhoModel):
    flow_plan_id: str
    status: WorkspaceFlowStatus
    completed_steps: list[str] = Field(default_factory=list)
    failed_step_id: str | None = None
    reason_code: str | None = None
    evidence_refs: list[dict[str, str]] = Field(default_factory=list)

