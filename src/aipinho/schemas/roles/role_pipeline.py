from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class RolePipelinePassDefinition(AIpinhoModel):
    pass_id: str
    role_id: str
    required: bool = True


class RolePipeline(AIpinhoModel):
    pipeline_id: str
    enabled: bool = True
    description: str = ""
    allowed_intents: list[str] = Field(default_factory=list)
    required_inputs: list[str] = Field(default_factory=list)
    passes: list[RolePipelinePassDefinition] = Field(default_factory=list)


class RolePipelineConfig(AIpinhoModel):
    schema_version: int
    pipelines: dict[str, RolePipeline]
