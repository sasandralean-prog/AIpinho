from __future__ import annotations
from typing import Any
from pydantic import Field
from aipinho.schemas.common.base import AIpinhoModel

class GatePolicySnapshot(AIpinhoModel):
    validation_enabled: bool = True
    deterministic_only: bool = True
    policy_files: list[str] = Field(default_factory=list)
    settings: dict[str, Any] = Field(default_factory=dict)
