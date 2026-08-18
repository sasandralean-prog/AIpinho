from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.evaluation.evaluation_finding import EvaluationFinding
from aipinho.schemas.evaluation.evaluation_trace import EvaluationTraceItem
from aipinho.schemas.evaluation.fallback_decision import FallbackDecision
from aipinho.schemas.evaluation.retry_decision import RetryDecision

EvaluationStatus = Literal["accepted", "accepted_with_warnings", "rejected", "needs_retry", "degraded"]


class EvaluationResult(AIpinhoModel):
    evaluation_id: str
    status: EvaluationStatus
    score: float = 0.0
    contract_valid: bool = False
    safety_valid: bool = False
    evidence_valid: bool = False
    format_valid: bool = False
    truncation_detected: bool = False
    hallucination_signals: list[EvaluationFinding] = Field(default_factory=list)
    violations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    retry_decision: RetryDecision = Field(default_factory=RetryDecision)
    fallback_decision: FallbackDecision = Field(default_factory=FallbackDecision)
    trace: list[EvaluationTraceItem] = Field(default_factory=list)
