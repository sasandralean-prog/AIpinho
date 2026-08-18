from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

class UXProgressIndicator(AIpinhoModel):
    item_id: str
    label: str
    current: int = 0
    total: int = 0
    state: str = "pending"
    percent: float = 0.0
