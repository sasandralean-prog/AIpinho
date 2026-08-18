from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

SmokeStatus = Literal["disabled", "available", "unavailable", "degraded"]


class SmokeTestStatus(AIpinhoModel):
    manual_inference_enabled: bool = False
    smoke_test_enabled: bool = False
    real_inference_global_enabled: bool = False
    default_model: str = "stub.default"
    chat_auto_real_inference: bool = False
    report_auto_real_inference: bool = False
    analysis_auto_real_inference: bool = False
    profiles: list[dict[str, object]] = Field(default_factory=list)
    llama_cpp_status: dict[str, object] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    status: SmokeStatus = "disabled"
