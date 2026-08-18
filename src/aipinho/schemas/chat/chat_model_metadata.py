from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class ChatModelMetadata(AIpinhoModel):
    model_id: str = "stub.default"
    provider_id: str = "stub.local"
    profile_id: str | None = None
    real_inference: bool = False
    process_started: bool = False
    manual_only: bool = True
    tool_calling_enabled: bool = False
    network_enabled: bool = False
    write_enabled: bool = False
    rag_enabled: bool = False
    memory_write_enabled: bool = False
    warnings: list[str] = Field(default_factory=list)
