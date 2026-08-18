from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

class UXErrorMessage(AIpinhoModel):
    code: str
    human_message: str
    severity: str = "warning"
    recoverable: bool = True
    next_safe_action: str | None = None
