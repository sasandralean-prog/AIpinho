from __future__ import annotations

from aipinho.schemas.common.base import AIpinhoModel


class LifecycleMetadata(AIpinhoModel):
    created_at: str
    updated_at: str
    expires_at: str | None = None