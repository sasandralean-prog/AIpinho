from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.actor import Actor
from aipinho.schemas.common.base import AIpinhoModel

ToolCallMode = Literal["dry_run", "execute"]


class ToolCall(AIpinhoModel):
    tool_call_id: str = Field(default_factory=lambda: f"tool_call_{uuid4().hex}")
    tool_id: str
    input: dict[str, Any] = Field(default_factory=dict)
    draft_id: str | None = None
    preview_id: str | None = None
    approval_id: str | None = None
    session_id: str | None = None
    mode: ToolCallMode = "dry_run"
    requested_by: Actor = Field(default_factory=lambda: Actor(type="user", id="local_user"))
