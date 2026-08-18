from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

InvocationTraceStatus = Literal["preview", "blocked", "completed", "timeout", "error"]


class LlamaInvocationTrace(AIpinhoModel):
    provider_id: str = "llama_cpp.local"
    model_id: str = "llama.local.placeholder"
    status: InvocationTraceStatus = "preview"
    real_inference: bool = False
    sanitized_command: str | None = None
    timeout_seconds: int | None = None
    process_started: bool = False
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
