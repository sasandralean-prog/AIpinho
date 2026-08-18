from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

RolePassStatus = Literal["pending", "running", "completed", "failed", "rejected", "skipped", "degraded"]


class RolePassOutput(AIpinhoModel):
    output_id: str = Field(default_factory=lambda: f"role_output_{uuid4().hex}")
    role_id: str
    status: RolePassStatus = "pending"
    content: str = ""
    structured_output: dict[str, Any] = Field(default_factory=dict)
    source: str = "deterministic"
    evaluation_status: str | None = None
    warnings: list[str] = Field(default_factory=list)
    violations: list[str] = Field(default_factory=list)
