from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from aipinho.schemas.chat.chat_inference_mode import ChatInferenceMode
from aipinho.schemas.chat.chat_request import ChatContext
from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.models.manual_inference_request import ManualInferenceRequester


class ManualChatInferenceRequest(AIpinhoModel):
    message: str
    session_id: str | None = None
    mode: ChatInferenceMode = "manual_real_inference"
    profile_id: str = "llama_cpp_manual_small"
    model_id: str = "llama.local.placeholder"
    provider_id: str = "llama_cpp.local"
    allow_real_inference: bool = False
    operator_confirmed: bool = False
    include_trace: bool = False
    context: ChatContext | None = None
    requested_by: ManualInferenceRequester = Field(default_factory=ManualInferenceRequester)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _message_required(self) -> "ManualChatInferenceRequest":
        if not self.message.strip():
            raise ValueError("message_required")
        return self
