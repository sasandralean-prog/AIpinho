from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class ActionDefinition(AIpinhoModel):
    aliases: list[str] = Field(default_factory=list)
    category: str
    side_effect: bool = False
    requires_approval: bool = False
    capability: str | None = None
    semantic_dependency_mode: Literal[
        "deterministic",
        "interpreted",
    ] = "interpreted"
    semantic_use_safety_dimensions: list[str] | None = None
    approval_exception_reason: str | None = None


class ActionRegistryConfig(AIpinhoModel):
    schema_version: int
    actions: dict[str, ActionDefinition]
