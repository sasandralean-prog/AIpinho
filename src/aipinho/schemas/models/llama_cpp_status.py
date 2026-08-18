from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

LlamaCppProviderStatus = Literal["disabled", "available", "unavailable", "degraded"]


class LlamaCppStatus(AIpinhoModel):
    provider_id: str = "llama_cpp.local"
    enabled: bool = False
    real_inference_enabled: bool = False
    executable_configured: bool = False
    executable_valid: bool = False
    model_configured: bool = False
    model_valid: bool = False
    models: list[dict[str, object]] = Field(default_factory=list)
    default_blocked_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    status: LlamaCppProviderStatus = "disabled"
