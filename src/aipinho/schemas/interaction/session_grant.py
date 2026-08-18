from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

SessionGrantStatus = Literal["pending", "approved", "denied", "expired", "revoked"]
SessionGrantScope = Literal["single_use", "session", "task", "permanent_preview"]


class SessionGrant(AIpinhoModel):
    grant_id: str
    session_id: str
    workspace_id: str | None = None
    workspace_path: str | None = None
    actions: list[str] = Field(default_factory=list)
    paths_scope: list[str] = Field(default_factory=list)
    command_scope: list[str] = Field(default_factory=list)
    scope: SessionGrantScope = "single_use"
    source_channel: str = "api"
    approved_by: str | None = None
    status: SessionGrantStatus = "pending"
    expires_at: datetime | None = None
    max_uses: int | None = 1
    used_count: int = 0
    created_at: datetime
    updated_at: datetime
    reason: str = ""
    evidence: list[dict[str, object]] = Field(default_factory=list)


class SessionGrantDecision(AIpinhoModel):
    grant_id: str
    status: SessionGrantStatus
    reason_code: str
    grant: SessionGrant
