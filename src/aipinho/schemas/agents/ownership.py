from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


LockScope = Literal["workspace", "directory", "file", "task"]
LockStatus = Literal["active", "released", "expired", "overridden"]


class WorkspaceLock(AIpinhoModel):
    lock_id: str = Field(default_factory=lambda: f"lock_{uuid4().hex}")
    workspace: str
    owner_agent: str
    owner_task_id: str | None = None
    bridge_task_id: str | None = None
    scope: LockScope = "workspace"
    locked_paths: list[str] = Field(default_factory=list)
    reason: str = ""
    created_at: str = Field(default_factory=utc_now_iso)
    expires_at: str | None = None
    released_at: str | None = None
    status: LockStatus = "active"
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class WorkspaceLockCreateRequest(AIpinhoModel):
    workspace: str
    owner_agent: str
    owner_task_id: str | None = None
    bridge_task_id: str | None = None
    scope: LockScope = "workspace"
    locked_paths: list[str] = Field(default_factory=list)
    reason: str = ""
    ttl_seconds: int = 1800
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class WorkspaceLockReleaseRequest(AIpinhoModel):
    actor_agent: str = "user"
    reason: str = ""


class WorkspaceLockOverrideRequest(AIpinhoModel):
    actor_agent: str = "user"
    reason: str


class WriteConflictCheckRequest(AIpinhoModel):
    workspace: str
    actor_agent: str
    owner_task_id: str | None = None
    bridge_task_id: str | None = None
    target_paths: list[str] = Field(default_factory=list)
    operation_type: str = "write"


class WriteConflictDecision(AIpinhoModel):
    allowed: bool
    status: str
    reason_code: str = "no_conflict"
    message: str
    conflicting_locks: list[WorkspaceLock] = Field(default_factory=list)


class TaskOwnership(AIpinhoModel):
    owner_agent: str
    supervisor_agent: str | None = None
    source_agent: str
    target_agent: str
    can_write: bool = False
    can_execute_shell: bool = False
    can_approve: bool = False
    can_cancel: bool = True
    can_generate_artifact: bool = True
    bridge_task_id: str | None = None
    owner_task_id: str | None = None
    workspace: str | None = None


class AgentHopCheckRequest(AIpinhoModel):
    source_agent: str
    target_agent: str
    lineage: list[str] = Field(default_factory=list)
    max_agent_hops: int = 1
    recursion_allowed: bool = False


class AgentHopDecision(AIpinhoModel):
    allowed: bool
    reason_code: str
    message: str
    hop_count: int
    lineage: list[str] = Field(default_factory=list)

