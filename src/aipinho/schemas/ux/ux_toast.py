from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

class UXToast(AIpinhoModel):
    toast_id: str
    message: str
    severity: str = "info"
    visible: bool = True
