from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


class UniversalTask(AIpinhoModel):
    task_id: str = Field(default_factory=lambda: f"task_{uuid4().hex}")
    operation_id: str = Field(default_factory=lambda: f"op_{uuid4().hex}")
    task_run_id: str = Field(default_factory=lambda: f"task_run_{uuid4().hex}")
    runtime_profile: str
    workspace_id: str | None = None
    project_id: str | None = None
    session_id: str | None = None
    workspace: str | None = None
    operation_type: str | None = None
    contract_type: str
    current_sprint: str | None = None
    current_phase: str | None = None
    parent_task_id: str | None = None
    source_channel: str = "runtime"
    created_at: str = Field(default_factory=utc_now_iso)
    context: dict[str, Any] = Field(default_factory=dict)


class TaskBootstrapRequest(AIpinhoModel):
    session_id: str | None = None
    workspace: str | None = None
    contract_type: str
    operation_type: str | None = None
    runtime_profile: str | None = None
    requested_actions: list[str] = Field(default_factory=list)
    intent_map: dict[str, Any] = Field(default_factory=dict)
    source_channel: str = "runtime"
    task_id: str | None = None
    operation_id: str | None = None
    task_run_id: str | None = None
    workspace_id: str | None = None
    project_id: str | None = None
    parent_task_id: str | None = None


class TaskBootstrapResult(AIpinhoModel):
    status: str = "created"
    universal_task: UniversalTask
    requires_task: bool = True
    execution_allowed_to_start: bool = False
    reason_code: str = "task_bootstrap_created"
