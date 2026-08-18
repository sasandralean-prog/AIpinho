from __future__ import annotations

from aipinho.schemas.chat.chat_request import ChatContext, ChatRequest


class ChatContextBuilder:
    def build(self, request: ChatRequest) -> ChatContext:
        return request.context or ChatContext(surface="api")