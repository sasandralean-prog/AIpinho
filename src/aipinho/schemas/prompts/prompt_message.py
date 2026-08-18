from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

PromptRole = Literal["system", "developer", "user", "assistant", "tool", "context"]


class PromptMessage(AIpinhoModel):
    role: PromptRole
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
