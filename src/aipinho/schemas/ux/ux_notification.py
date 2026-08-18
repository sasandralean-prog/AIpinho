from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

class UXNotification(AIpinhoModel):
    notification_id: str
    event_type: str
    severity: str = "info"
    human_message: str
    dedupe_key: str | None = None
    acknowledged: bool = False
    created_at: str | None = None
