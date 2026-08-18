from __future__ import annotations
from typing import Any, Literal
from pydantic import Field
from aipinho.schemas.common.actor import Actor
from aipinho.schemas.common.base import AIpinhoModel

TaskRunSourceType = Literal["draft", "preview", "direct"]

class TaskRunRequest(AIpinhoModel):
    source_type: TaskRunSourceType = "direct"
    task_id: str | None = None
    operation_id: str | None = None
    task_run_id: str | None = None
    workspace_id: str | None = None
    project_id: str | None = None
    parent_task_id: str | None = None
    source_channel: str = "runtime"
    draft_id: str | None = None
    preview_id: str | None = None
    session_id: str | None = None
    workspace: str | None = None
    contract_type: str = "readonly_analysis"
    operation_type: str | None = None
    runtime_profile: str | None = None
    capabilities_required: list[str] = Field(default_factory=list)
    intent_map: dict[str, Any] = Field(default_factory=dict)
    policy_decision: dict[str, Any] = Field(default_factory=dict)
    context_injection_plan_id: str | None = None
    approval_id: str | None = None
    requested_actions: list[str] = Field(default_factory=list)
    mode: Literal[
        "read_only",
        "governed",
        "write_file",
        "shell",
        "patch",
        "artifact",
        "validation",
    ] = "governed"
    start_immediately: bool = False
    include_trace: bool = False
    requested_by: Actor = Field(default_factory=lambda: Actor(type="user", id="local_operator"))
