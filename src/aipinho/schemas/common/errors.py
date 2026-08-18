from __future__ import annotations

from aipinho.schemas.common.base import AIpinhoModel


class ErrorResponse(AIpinhoModel):
    code: str
    message: str
    details: dict[str, object] | None = None
