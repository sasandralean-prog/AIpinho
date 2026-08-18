from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class ModelProvider(AIpinhoModel):
    provider_id: str
    type: str
    enabled: bool = False
    local: bool = True
    real_inference: bool = False
    supports_streaming: bool = False
    supports_tools: bool = False
    supports_json_mode: bool = False
    supports_mmproj: bool = False
    supports_first_token_probe: bool = False
    auto_load_enabled: bool = False
    modalities: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    executable_path: str | None = None
    server_executable_path: str | None = None
    execution_mode: str = "cli"
    notes: list[str] = Field(default_factory=list)

