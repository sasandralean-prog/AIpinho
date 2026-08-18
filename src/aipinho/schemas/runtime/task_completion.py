from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

CompletionStatus = Literal["completed", "completed_with_limitations", "partial", "failed", "blocked", "cancelled"]
CriterionStatus = Literal["fulfilled", "missing", "degraded", "not_applicable"]


class TaskCompletionCriterion(AIpinhoModel):
    criterion_id: str
    kind: str
    required: bool = True
    status: CriterionStatus = "missing"
    summary: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskCompletionEvaluation(AIpinhoModel):
    status: CompletionStatus = "partial"
    safe_to_report_success: bool = False
    expected_outcomes: list[str] = Field(default_factory=list)
    fulfilled_outcomes: list[str] = Field(default_factory=list)
    missing_outcomes: list[str] = Field(default_factory=list)
    criteria: list[TaskCompletionCriterion] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
