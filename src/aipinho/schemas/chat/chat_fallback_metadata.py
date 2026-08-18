from __future__ import annotations

from aipinho.schemas.common.base import AIpinhoModel


class ChatFallbackMetadata(AIpinhoModel):
    fallback_used: bool = False
    fallback_type: str | None = None
    reason: str | None = None
    rejected_model_content_hidden: bool = True
    safe_message: str | None = None
