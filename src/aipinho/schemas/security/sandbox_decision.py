from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

SandboxDecisionStatus = Literal["allowed", "blocked", "invalid", "degraded"]


class SandboxDecision(AIpinhoModel):
    status: SandboxDecisionStatus
    allowed: bool = False
    reason: str
    workspace: str | None = None
    target_path: str | None = None
    normalized_workspace: str | None = None
    normalized_target_path: str | None = None
    violations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    trace: list[dict[str, Any]] = Field(default_factory=list)
