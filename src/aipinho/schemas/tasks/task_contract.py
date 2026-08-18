from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

ContractType = Literal[
    "conversation",
    "readonly_analysis",
    "artifact_generation",
    "filesystem_write",
    "file_modification",
    "project_generation",
    "artifact_build",
    "shell_execution",
    "web_search",
    "project_build",
    "patch_request",
    "patch_apply",
    "validation",
    "validation_request",
    "in_chat_final_report",
    "memory_curation",
    "unknown",
]


class TaskContractInput(AIpinhoModel):
    task_type: ContractType = "unknown"
    operation_type: str | None = None
    intent_type: str | None = None
    source_scope: str | None = None
    workspace_ref: str | None = None
    requested_actions: list[str] = Field(default_factory=list)
    capabilities_required: list[str] = Field(default_factory=list)
    tools_required: list[str] = Field(default_factory=list)
    side_effects: list[str] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    approval_scope: str | None = None
    runtime_profile: str | None = None
    read_only: bool = True
    approval_requested: bool = False
    safe_to_preview: bool = False
    safe_to_execute: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskContract(AIpinhoModel):
    task_type: ContractType
    operation_type: str | None = None
    intent_type: str | None = None
    source_scope: str | None = None
    workspace_ref: str | None = None
    requested_actions: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    tools_required: list[str] = Field(default_factory=list)
    side_effects: list[str] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    approval_scope: str | None = None
    runtime_profile: str | None = None
    read_only: bool = True
    requires_approval: bool = False
    safe_to_preview: bool = False
    safe_to_execute: bool = False
    policy_decision: dict[str, Any] = Field(default_factory=dict)
    approval_decision: dict[str, Any] = Field(default_factory=dict)


class TaskContractPreview(AIpinhoModel):
    contract_type: ContractType
    operation_type: str | None = None
    runtime_profile: str | None = None
    requires_task: bool = False
    requires_workspace: bool = False
    requested_actions: list[str] = Field(default_factory=list)
    allowed_actions: list[str] = Field(default_factory=list)
    denied_actions: list[str] = Field(default_factory=list)
    approval_required_for: list[str] = Field(default_factory=list)
    safe_to_preview: bool = False
    safe_to_execute: bool = False
    policy_decision_id: str
