from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


WorkspaceRole = Literal[
    "source_readonly",
    "target_mutable",
    "external_inbox",
    "artifact_output",
    "system_mutable",
    "protected",
    "temp_staging",
    "forbidden",
]


class WorkspaceRoleContract(AIpinhoModel):
    workspace_id: str
    root_path: str
    role: WorkspaceRole
    read_allowed: bool = False
    write_allowed: bool = False
    shell_allowed: bool = False
    patch_allowed: bool = False
    approval_required: bool = True
    allowed_operations: list[str] = Field(default_factory=list)
    forbidden_operations: list[str] = Field(default_factory=list)
    max_risk_without_approval: str = "none"
    human_label: str = ""
    reason: str = ""
    evidence: list[str] = Field(default_factory=list)
    matched_root: str | None = None
    path_within_workspace: bool = False


class WorkspaceRoleDecision(AIpinhoModel):
    status: Literal["allowed", "denied", "needs_clarification"]
    contract: WorkspaceRoleContract | None = None
    reason: str
    warnings: list[str] = Field(default_factory=list)
    trace: list[dict[str, object]] = Field(default_factory=list)
