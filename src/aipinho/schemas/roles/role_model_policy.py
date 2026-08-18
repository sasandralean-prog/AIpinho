from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class RoleModelPolicy(AIpinhoModel):
    require_model_registered: bool = True
    require_model_enabled: bool = True
    require_provider_enabled: bool = True
    require_capability_match: bool = True
    require_hardware_policy_match: bool = True
    require_doctor_healthy_or_degraded_allowed: bool = True
    allow_degraded_models: bool = True
    blocked_auto_models: list[str] = Field(default_factory=list)
