from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

ModelResponseStatus = Literal["completed", "blocked", "degraded", "error"]
FinishReason = Literal["stop", "length", "blocked", "error", "timeout"]


class ModelUsage(AIpinhoModel):
    input_chars: int = 0
    output_chars: int = 0
    estimated_input_tokens: int = 0
    estimated_output_tokens: int = 0


class ModelResponse(AIpinhoModel):
    response_id: str = Field(default_factory=lambda: f"model_response_{uuid4().hex}")
    request_id: str
    model_id: str
    provider_id: str
    status: ModelResponseStatus
    content: str
    structured_output: dict[str, Any] | None = None
    usage: ModelUsage = Field(default_factory=ModelUsage)
    finish_reason: FinishReason = "stop"
    real_inference: bool = False
    warnings: list[str] = Field(default_factory=list)
    trace: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    evaluation_result: dict[str, Any] | None = None


