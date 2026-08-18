from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from pydantic import Field
from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.runtime.task_run_plan import TaskRunPlan
from aipinho.schemas.runtime.canonical_operation_state import CanonicalOperationState
from aipinho.schemas.runtime.execution_graph import ExecutionGraph
from aipinho.schemas.runtime.workflow_runtime import WorkflowRuntimeInstance
from aipinho.schemas.runtime.workspace_context import ExecutionContext, RetrievalContext, WorkspaceContext
from aipinho.schemas.runtime.task_run_state import TaskRunStatus
from aipinho.schemas.runtime.task_run_trace import TaskRunTraceItem
from aipinho.schemas.runtime.task_block_cause import TaskBlockCause

class TaskRun(AIpinhoModel):
    run_id: str
    task_id: str | None = None
    operation_id: str | None = None
    task_run_id: str | None = None
    workspace_id: str | None = None
    project_id: str | None = None
    parent_task_id: str | None = None
    current_sprint: str | None = None
    current_phase: str | None = None
    bootstrap_context: dict[str, Any] = Field(default_factory=dict)
    source_type: str
    draft_id: str | None = None
    preview_id: str | None = None
    approval_id: str | None = None
    session_id: str | None = None
    workspace: str | None = None
    contract_type: str = "readonly_analysis"
    operation_type: str | None = None
    runtime_profile: str | None = None
    capabilities_required: list[str] = Field(default_factory=list)
    requested_actions: list[str] = Field(default_factory=list)
    intent_map: dict[str, Any] = Field(default_factory=dict)
    status: TaskRunStatus = "created"
    mode: str = "read_only"
    plan: TaskRunPlan
    workflow: WorkflowRuntimeInstance | None = None
    execution_graph: ExecutionGraph | None = None
    current_step_id: str | None = None
    policy_snapshot: dict[str, Any] = Field(default_factory=dict)
    context_injection_plan_id: str | None = None
    workspace_snapshot: dict[str, Any] = Field(default_factory=dict)
    workspace_context: WorkspaceContext | None = None
    retrieval_context: RetrievalContext | None = None
    execution_context: ExecutionContext | None = None
    canonical_state: CanonicalOperationState | None = None
    produced_artifacts: list[dict[str, Any]] = Field(default_factory=list)
    required_artifacts: list[str] = Field(default_factory=list)
    missing_artifacts: list[str] = Field(default_factory=list)
    approval_snapshot: dict[str, Any] = Field(default_factory=dict)
    auto_run_requested: bool = False
    cancellation_requested: bool = False
    cancellation_reason: str | None = None
    revision: int = 1
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: str | None = None
    finished_at: str | None = None
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    block_cause: TaskBlockCause | None = None
    trace: list[TaskRunTraceItem] = Field(default_factory=list)
