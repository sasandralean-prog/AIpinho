from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class ModelCapabilityProfile(AIpinhoModel):
    model_id: str
    provider_id: str
    capabilities: list[str] = Field(default_factory=list)
    modality: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


ModelCapability = str
