from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.actor import Actor
from aipinho.schemas.common.base import AIpinhoModel

ToolExecutionMode = Literal["readonly", "governed"]


class ToolExecutionRequest(AIpinhoModel):
    tool_execution_request_id: str = Field(default_factory=lambda: f"tool_exec_req_{uuid4().hex}")
    tool_id: str
    input: dict[str, Any] = Field(default_factory=dict)
    session_id: str | None = None
    draft_id: str | None = None
    preview_id: str | None = None
    approval_id: str | None = None
    mode: ToolExecutionMode = "readonly"
    include_content: bool = True
    include_trace: bool = False
    requested_by: Actor = Field(default_factory=lambda: Actor(type="user", id="local_user"))
