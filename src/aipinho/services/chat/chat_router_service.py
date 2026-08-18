from __future__ import annotations

from aipinho.schemas.chat.chat_request import ChatMode, ChatRequest


class ChatRouterService:
    def force_preview(self, request: ChatRequest) -> ChatRequest:
        data = request.model_dump() if hasattr(request, "model_dump") else request.dict()
        data["mode"] = "preview"
        data["include_trace"] = True
        return ChatRequest(**data)

    def mode(self, request: ChatRequest) -> ChatMode:
        return request.mode