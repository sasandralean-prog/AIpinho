from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.models.model_definition import ModelDefinition


class ModelRegistrySnapshot(AIpinhoModel):
    status: str = "ok"
    models: list[ModelDefinition] = Field(default_factory=list)
    compat_models: list[ModelDefinition] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
