from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class LocalModelPath(AIpinhoModel):
    entry_id: str
    model_id: str
    provider_id: str = "llama_cpp.local"
    enabled: bool = False
    path: str | None = None
    format: str = "gguf"
    quantization: str | None = None
    size_bytes: int | None = None
    context_window_tokens: int = 4096
    notes: list[str] = Field(default_factory=list)
