from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.chat.chat_evaluation_metadata import ChatEvaluationMetadata
from aipinho.schemas.chat.chat_fallback_metadata import ChatFallbackMetadata
from aipinho.schemas.chat.chat_inference_trace import ChatInferenceTraceItem
from aipinho.schemas.chat.chat_model_metadata import ChatModelMetadata
from aipinho.schemas.common.base import AIpinhoModel

ManualChatInferenceStatus = Literal["ok", "preview", "blocked", "unavailable", "timeout", "rejected", "fallback", "degraded", "error"]


class ManualChatInferenceResponse(AIpinhoModel):
    response_id: str = Field(default_factory=lambda: f"manual_chat_{uuid4().hex}")
    session_id: str | None = None
    status: ManualChatInferenceStatus = "blocked"
    message: str
    process_started: bool = False
    real_inference: bool = False
    model: ChatModelMetadata = Field(default_factory=ChatModelMetadata)
    evaluation: ChatEvaluationMetadata = Field(default_factory=ChatEvaluationMetadata)
    fallback: ChatFallbackMetadata = Field(default_factory=ChatFallbackMetadata)
    gate_decision: dict[str, Any] = Field(default_factory=dict)
    prompt_budget: dict[str, Any] = Field(default_factory=dict)
    prompt_preview: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    trace: list[ChatInferenceTraceItem] = Field(default_factory=list)
