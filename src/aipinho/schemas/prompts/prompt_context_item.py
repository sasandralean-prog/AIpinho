from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

ContextSourceType = Literal["session", "file", "report", "evidence", "policy", "intent", "user", "metadata"]


class PromptContextSafety(AIpinhoModel):
    contains_secret: bool = False
    blocked: bool = False
    reason: str | None = None


class PromptContextItem(AIpinhoModel):
    item_id: str = Field(default_factory=lambda: f"context_item_{uuid4().hex}")
    source_type: ContextSourceType
    priority: float = 0.0
    title: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    safety: PromptContextSafety = Field(default_factory=PromptContextSafety)
