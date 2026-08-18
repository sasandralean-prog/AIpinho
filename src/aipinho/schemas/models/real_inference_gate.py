from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

GateStatus = Literal["allowed", "blocked", "degraded", "unavailable"]


class RealInferenceGateRequirements(AIpinhoModel):
    provider_enabled: bool = False
    model_enabled: bool = False
    model_path_valid: bool = False
    executable_valid: bool = False
    safety_envelope_present: bool = False
    output_contract_present: bool = False
    budget_valid: bool = False


class RealInferenceGateDecision(AIpinhoModel):
    allowed: bool = False
    status: GateStatus = "blocked"
    provider_id: str = "llama_cpp.local"
    model_id: str = "llama.local.placeholder"
    real_inference_enabled: bool = False
    request_opt_in: bool = False
    blocked_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    requirements: RealInferenceGateRequirements = Field(default_factory=RealInferenceGateRequirements)
    trace: list[dict[str, object]] = Field(default_factory=list)
