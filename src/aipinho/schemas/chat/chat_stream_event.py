from __future__ import annotations

from typing import Literal

from aipinho.schemas.common.base import AIpinhoModel

ChatStreamEventType = Literal["message_start", "message_delta", "message_complete", "error"]


class ChatStreamEvent(AIpinhoModel):
    event_type: ChatStreamEventType
    response_id: str
    chunk_index: int = 0
    chunk_total: int = 1
    text: str = ""