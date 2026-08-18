from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

class UXStatus(AIpinhoModel):
    status: str = "ok"
    enabled: bool = True
    hardening_policies_loaded: list[str] = Field(default_factory=list)
    features: dict[str, bool] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
