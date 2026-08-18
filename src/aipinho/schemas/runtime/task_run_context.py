from __future__ import annotations
from typing import Any
from pydantic import Field
from aipinho.schemas.common.base import AIpinhoModel

class TaskRunContext(AIpinhoModel):
    run_id: str
    workspace: str | None = None
    prompt_summary: str = ""
    outputs: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    blocked_items: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
