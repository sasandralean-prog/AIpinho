from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class ModelProbeResult(AIpinhoModel):
    model_id: str
    status: str
    probe_type: str = "metadata"
    first_token_probe_executed: bool = False
    blocked_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)
