from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


GitOperationClass = Literal[
    "local_read",
    "network_read",
    "worktree_write",
    "commit",
    "push",
    "destructive",
    "unknown",
]


class GitCommandClassification(AIpinhoModel):
    operation_class: GitOperationClass
    operation: str
    capability: str
    capabilities_required: list[str] = Field(default_factory=list)
    network_required: bool = False
    requires_remote_scope: bool = False
    worktree_mutation: bool = False
    destructive: bool = False
    safe_for_governed_execution: bool = False
    remote_name: str | None = None
    branch: str | None = None
    reason_code: str
