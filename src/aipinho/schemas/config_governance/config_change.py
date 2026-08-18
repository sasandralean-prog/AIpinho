from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.common.actor import Actor
from aipinho.schemas.common.base import AIpinhoModel

ConfigChangeStatus = Literal[
    "draft",
    "previewed",
    "approval_required",
    "approved",
    "applied",
    "cancelled",
    "failed",
]

ConfigTarget = Literal[
    "workspace_registry",
    "artifact_policy",
    "patch_policy",
    "governed_tool_execution_policy",
    "provider_policy",
    "agent_registry",
]


class ConfigChangeRequest(AIpinhoModel):
    target: ConfigTarget
    operation: Literal["replace", "merge", "add_workspace", "update_workspace", "set_permissions"]
    payload: dict[str, object]
    reason: str = ""
    actor: Actor = Field(default_factory=Actor)
    requires_approval: bool | None = None


class ConfigChangePreview(AIpinhoModel):
    change_id: str
    target: ConfigTarget
    status: ConfigChangeStatus
    requires_approval: bool
    sanitized_diff: str
    validation_status: Literal["ok", "failed"]
    validation_errors: list[str] = Field(default_factory=list)
    approval_id: str | None = None
    changed_paths: list[str] = Field(default_factory=list)
    events: list[dict[str, object]] = Field(default_factory=list)


class ConfigBackup(AIpinhoModel):
    backup_id: str
    change_id: str | None = None
    target: ConfigTarget
    path: str
    backup_path: str
    created_at: str
    sha256: str


class ConfigApplyResult(AIpinhoModel):
    change_id: str
    target: ConfigTarget
    status: Literal["applied", "failed"]
    backup_id: str | None = None
    reload_status: str
    self_check_status: str
    errors: list[str] = Field(default_factory=list)
    events: list[dict[str, object]] = Field(default_factory=list)


class ConfigChangeRecord(AIpinhoModel):
    change_id: str
    request: ConfigChangeRequest
    status: ConfigChangeStatus = "draft"
    created_at: str
    updated_at: str
    approval_id: str | None = None
    preview: ConfigChangePreview | None = None
    apply_result: ConfigApplyResult | None = None
    errors: list[str] = Field(default_factory=list)
    events: list[dict[str, object]] = Field(default_factory=list)

