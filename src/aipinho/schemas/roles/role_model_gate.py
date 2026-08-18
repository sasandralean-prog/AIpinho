from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

RoleModelGateStatus = Literal["allowed", "blocked", "degraded", "deterministic_only"]


class RoleModelGateRequest(AIpinhoModel):
    role_id: str
    model_policy: str = "stub_only"
    requested_model_id: str | None = None
    purpose: str = "chat"
    prompt_assembly: dict[str, object] = Field(default_factory=dict)
    output_contract: dict[str, object] = Field(default_factory=dict)
    safety_envelope: dict[str, object] = Field(default_factory=dict)
    allow_real_inference: bool = False
    operator_confirmed: bool = False


class RoleModelGateDecision(AIpinhoModel):
    allowed: bool = False
    status: RoleModelGateStatus = "blocked"
    role_id: str
    model_id: str = "stub.default"
    provider_id: str = "stub.local"
    real_inference: bool = False
    blocked_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    trace: list[dict[str, object]] = Field(default_factory=list)
