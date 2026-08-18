from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field, model_validator

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.models.generation_config import GenerationConfig
from aipinho.schemas.prompts.prompt_message import PromptMessage


class ModelRequest(AIpinhoModel):
    request_id: str = Field(default_factory=lambda: f"model_request_{uuid4().hex}")
    model_id: str = "stub.default"
    provider_id: str = "stub.local"
    messages: list[PromptMessage]
    generation_config: GenerationConfig = Field(default_factory=GenerationConfig)
    output_contract: dict[str, Any] = Field(default_factory=dict)
    safety_envelope: dict[str, Any] = Field(default_factory=dict)
    trace: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _messages_required(self) -> "ModelRequest":
        if not self.messages:
            raise ValueError("messages_required")
        return self
