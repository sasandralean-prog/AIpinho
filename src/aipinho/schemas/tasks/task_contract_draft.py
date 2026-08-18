from __future__ import annotations

from typing import Any

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.tasks.task_draft_state import TaskDraftStatus, WorkspaceDraftStatus


class TaskDraftWorkspace(AIpinhoModel):
    path: str | None = None
    status: WorkspaceDraftStatus = "missing"


class TaskContractDraft(AIpinhoModel):
    draft_id: str
    session_id: str | None = None
    status: TaskDraftStatus = "draft"
    intent_map: dict[str, Any] = Field(default_factory=dict)
    policy_decision: dict[str, Any] = Field(default_factory=dict)
    contract_type: str = "unknown"
    operation_type: str = "unknown"
    intent_type: str = "unknown"
    runtime_profile: str | None = None
    capabilities_required: list[str] = Field(default_factory=list)
    source_scope: str | None = None
    requires_workspace: bool = False
    workspace: TaskDraftWorkspace = Field(default_factory=TaskDraftWorkspace)
    requested_actions: list[str] = Field(default_factory=list)
    allowed_actions: list[str] = Field(default_factory=list)
    denied_actions: list[str] = Field(default_factory=list)
    approval_required_for: list[str] = Field(default_factory=list)
    executable_plan_ref: str | None = None
    expected_outcomes: list[str] = Field(default_factory=list)
    safe_to_execute: bool = False
    safe_to_preview: bool = False
    clarifying_questions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    trace: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str
    updated_at: str
    expires_at: str | None = None
