from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

WorkspaceRegistryRole = Literal[
    "source_readonly",
    "target_mutable",
    "external_inbox",
    "artifact_output",
    "system_mutable",
    "protected",
    "temp_staging",
    "forbidden",
]

PermissionName = Literal[
    "read_file",
    "list_files",
    "create_file",
    "modify_file",
    "apply_patch",
    "artifact_create",
    "copy_from",
    "copy_to",
    "move_from",
    "move_to",
    "delete_file",
    "shell_readonly",
    "shell_build",
    "shell_test",
    "script_execution",
    "network_download",
    "git_commit",
    "git_push",
]

PermissionValue = Literal["allowed", "ask", "denied"]


class WorkspaceEntry(AIpinhoModel):
    workspace_id: str
    root_path: str
    role: WorkspaceRegistryRole
    human_label: str = ""
    reason: str = ""
    approval_required: bool = True
    enabled: bool = True
    permissions: dict[PermissionName, PermissionValue] = Field(default_factory=dict)
    evidence: list[str] = Field(default_factory=list)


class WorkspacePreviewRequest(AIpinhoModel):
    root_path: str
    role: WorkspaceRegistryRole
    workspace_id: str | None = None
    permissions: dict[PermissionName, PermissionValue] = Field(default_factory=dict)


class WorkspacePermissionDecision(AIpinhoModel):
    status: Literal["allowed", "approval_required", "denied"]
    reason_code: str
    permission: PermissionName
    permission_value: PermissionValue
    workspace_id: str | None = None
    workspace_role: WorkspaceRegistryRole | None = None
    root_path: str | None = None
    target_path: str | None = None
    trace: list[dict[str, object]] = Field(default_factory=list)


class WorkspaceRegistryPayload(AIpinhoModel):
    schema_version: int = 1
    defaults: dict[str, object] = Field(default_factory=dict)
    role_defaults: dict[WorkspaceRegistryRole, dict[PermissionName, PermissionValue]] = Field(default_factory=dict)
    workspaces: list[WorkspaceEntry] = Field(default_factory=list)

