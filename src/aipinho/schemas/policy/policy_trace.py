from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

PolicyDecisionStatus = Literal["allowed", "denied", "needs_approval", "needs_clarification", "degraded"]
Severity = Literal["info", "warning", "error", "critical"]


class PolicyPrecedenceConfig(AIpinhoModel):
    schema_version: int
    precedence: list[str]
    rules: dict[str, object] = Field(default_factory=dict)


class PolicyTraceItem(AIpinhoModel):
    stage: str
    rule: str
    decision: str
    reason: str
    severity: Severity = "info"
    source: str
    input: dict[str, object] = Field(default_factory=dict)


class PolicyTrace(AIpinhoModel):
    items: list[PolicyTraceItem] = Field(default_factory=list)