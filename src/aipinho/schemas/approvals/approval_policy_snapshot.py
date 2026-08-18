from __future__ import annotations

from typing import Any

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class ApprovalPolicySnapshot(AIpinhoModel):
    policy_decision_id: str | None = None
    policy_status: str = "unknown"
    allowed_actions: list[str] = Field(default_factory=list)
    denied_actions: list[str] = Field(default_factory=list)
    approval_required_for: list[str] = Field(default_factory=list)
    granted_capabilities: list[str] = Field(default_factory=list)
    denied_capabilities: list[str] = Field(default_factory=list)
    workspace_status: str = "unknown"
    risk_level: str = "unknown"
    trace_hash: str = ""
    config_versions: dict[str, Any] = Field(default_factory=dict)