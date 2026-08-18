from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


class WorkspaceContext(AIpinhoModel):
    context_id: str = Field(default_factory=lambda: f"workspace_context_{uuid4().hex}")
    workspace_id: str | None = None
    workspace_path: str | None = None
    workspace_role: str | None = None
    project_id: str | None = None
    project_name: str | None = None
    project_root: str | None = None
    external_roots: list[str] = Field(default_factory=list)
    library_roots: list[str] = Field(default_factory=list)
    readonly_flags: dict[str, bool] = Field(default_factory=dict)
    workspace_ids: list[str] = Field(default_factory=list)
    artifact_store: str | None = None
    retrieval_scope: dict[str, Any] = Field(default_factory=dict)
    allowed_roots: list[str] = Field(default_factory=list)
    runtime_profile: str | None = None
    current_phase: str | None = None
    current_task: str | None = None
    source: str = "workspace_context_service"
    warnings: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)


class RetrievalContext(AIpinhoModel):
    retrieval_context_id: str = Field(default_factory=lambda: f"retrieval_context_{uuid4().hex}")
    workspace_id: str | None = None
    retrieval_scope: dict[str, Any] = Field(default_factory=dict)
    allowed_roots: list[str] = Field(default_factory=list)
    artifact_scope: str | None = None
    runtime_profile: str | None = None
    task_id: str | None = None
    task_run_id: str | None = None
    phase: str | None = None
    source: str = "workspace_context"
    valid: bool = True
    blocked_reasons: list[str] = Field(default_factory=list)


class ExecutionContext(AIpinhoModel):
    execution_context_id: str = Field(default_factory=lambda: f"execution_context_{uuid4().hex}")
    task_id: str | None = None
    task_run_id: str | None = None
    operation_id: str | None = None
    session_id: str | None = None
    workspace_context: WorkspaceContext | None = None
    retrieval_context: RetrievalContext | None = None
    project_context: dict[str, Any] = Field(default_factory=dict)
    runtime_context: dict[str, Any] = Field(default_factory=dict)
    current_phase: str | None = None
    phase_history: list[dict[str, Any]] = Field(default_factory=list)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    dependencies: list[dict[str, Any]] = Field(default_factory=list)
    runtime_profile: str | None = None
    updated_at: str = Field(default_factory=utc_now_iso)
