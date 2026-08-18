from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

EstimateConfidence = Literal["low", "medium", "high"]


class ModelRuntimeEstimate(AIpinhoModel):
    estimated_ram_gb: float = 0.0
    confidence: EstimateConfidence = "low"
    warnings: list[str] = Field(default_factory=list)
    blocking: bool = False
    model_size_bytes: int | None = None
    ctx_size: int = 0
    n_predict: int = 0
