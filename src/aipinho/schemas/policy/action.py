from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class ActionDefinition(AIpinhoModel):
    aliases: list[str] = Field(default_factory=list)
    category: str
    side_effect: bool = False
    requires_approval: bool = False
    capability: str | None = None
    approval_exception_reason: str | None = None


class ActionRegistryConfig(AIpinhoModel):
    schema_version: int
    actions: dict[str, ActionDefinition]
