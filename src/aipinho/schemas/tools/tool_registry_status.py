from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class ToolRegistryStatus(AIpinhoModel):
    status: str
    tools: int = 0
    enabled_tools: int = 0
    disabled_tools: int = 0
    adapters: dict[str, str] = Field(default_factory=dict)
    real_execution_enabled: bool = False
    warnings: list[str] = Field(default_factory=list)
