from __future__ import annotations

from aipinho.schemas.common.base import AIpinhoModel


class ModelFallbackResult(AIpinhoModel):
    fallback_model_id: str | None = None
    fallback_used: bool = False
    status: str = "not_used"
    reason: str | None = None
