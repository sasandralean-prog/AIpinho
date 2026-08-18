from __future__ import annotations

from aipinho.schemas.common.base import AIpinhoModel


class RoleFallback(AIpinhoModel):
    fallback_used: bool = False
    fallback_type: str | None = None
    message: str = ""
    skip_pass: bool = False
