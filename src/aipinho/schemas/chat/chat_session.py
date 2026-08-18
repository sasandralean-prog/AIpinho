from __future__ import annotations

from pydantic import Field

from aipinho.schemas.chat.chat_message import ChatMessage
from aipinho.schemas.chat.session_state import SessionState
from aipinho.schemas.common.base import AIpinhoModel


class ChatSession(AIpinhoModel):
    session_id: str
    messages: list[ChatMessage] = Field(default_factory=list)
    state: SessionState | None = None