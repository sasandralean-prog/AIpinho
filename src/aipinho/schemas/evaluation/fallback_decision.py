from __future__ import annotations

from aipinho.schemas.common.base import AIpinhoModel


class FallbackDecision(AIpinhoModel):
    should_fallback: bool = False
    fallback_type: str = "none"
    reason: str | None = None
    safe_message: str | None = None
