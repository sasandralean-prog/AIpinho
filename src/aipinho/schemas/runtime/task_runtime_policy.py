from __future__ import annotations
from typing import Any
from pydantic import Field
from aipinho.schemas.common.base import AIpinhoModel

class TaskRuntimePolicy(AIpinhoModel):
    enabled: bool = True
    mode: str = "read_only"
    allowed_contract_types: list[str] = Field(default_factory=list)
    allowed_actions: list[str] = Field(default_factory=list)
    blocked_actions: list[str] = Field(default_factory=list)
    settings: dict[str, Any] = Field(default_factory=dict)
