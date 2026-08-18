from __future__ import annotations

from typing import Any

from aipinho.schemas.chat.chat_inference_trace import ChatInferenceTraceItem


class ChatInferenceTraceService:
    def item(self, stage: str, status: str, reason: str | None = None, *, source: str | None = None, data: dict[str, Any] | None = None) -> ChatInferenceTraceItem:
        return ChatInferenceTraceItem(stage=stage, status=status, reason=reason, source=source, data=data or {})

    def visible(self, items: list[ChatInferenceTraceItem], *, include: bool) -> list[ChatInferenceTraceItem]:
        return items if include else []

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "chat_inference_trace"}
