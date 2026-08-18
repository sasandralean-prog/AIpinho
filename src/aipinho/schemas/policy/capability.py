from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class CapabilityDefinition(AIpinhoModel):
    description: str
    side_effect: bool = False
    aliases: list[str] = Field(default_factory=list)


class CapabilityRegistryConfig(AIpinhoModel):
    schema_version: int
    capabilities: dict[str, CapabilityDefinition] = Field(default_factory=dict)


class CapabilityDecision(AIpinhoModel):
    capability: str
    granted: bool
    reason: str
