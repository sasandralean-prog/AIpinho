from __future__ import annotations

from typing import Literal

from aipinho.schemas.common.base import AIpinhoModel

ChatMessageRole = Literal["user", "assistant", "system"]


class ChatMessage(AIpinhoModel):
    role: ChatMessageRole
    content: str
    message_id: str | None = None
    created_at: str | None = None