from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.roles.effective_role_policy import EffectiveRolePolicy
from aipinho.schemas.roles.role_model_gate import RoleModelGateDecision
from aipinho.schemas.roles.role_pass_output import RolePassOutput, RolePassStatus


class RolePass(AIpinhoModel):
    pass_id: str
    role_id: str
    required: bool = True
    status: RolePassStatus = "pending"
    input: dict[str, Any] = Field(default_factory=dict)
    effective_policy: EffectiveRolePolicy | None = None
    model_gate: RoleModelGateDecision | None = None
    prompt_assembly: dict[str, Any] = Field(default_factory=dict)
    model_response: dict[str, Any] = Field(default_factory=dict)
    evaluation_result: dict[str, Any] = Field(default_factory=dict)
    output: RolePassOutput | None = None
    warnings: list[str] = Field(default_factory=list)
    trace: list[dict[str, Any]] = Field(default_factory=list)
    started_at: str | None = None
    finished_at: str | None = None

    def mark_started(self) -> None:
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.status = "running"

    def mark_finished(self, status: RolePassStatus) -> None:
        self.finished_at = datetime.now(timezone.utc).isoformat()
        self.status = status
