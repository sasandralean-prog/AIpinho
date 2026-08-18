from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field, model_validator

from aipinho.schemas.common.base import AIpinhoModel

EvaluationPurpose = Literal["chat", "project_report", "code_analysis", "task_preview", "smoke_test"]


class EvaluationRequest(AIpinhoModel):
    evaluation_id: str = Field(default_factory=lambda: f"evaluation_{uuid4().hex}")
    model_response: dict[str, Any]
    model_request: dict[str, Any] = Field(default_factory=dict)
    prompt_assembly: dict[str, Any] = Field(default_factory=dict)
    output_contract: dict[str, Any] = Field(default_factory=dict)
    safety_envelope: dict[str, Any] = Field(default_factory=dict)
    evidence_context: list[dict[str, Any]] = Field(default_factory=list)
    context_injection_plan: dict[str, Any] = Field(default_factory=dict)
    policy_decision: dict[str, Any] = Field(default_factory=dict)
    purpose: EvaluationPurpose = "chat"
    include_trace: bool = False

    @model_validator(mode="after")
    def _model_response_required(self) -> "EvaluationRequest":
        if not self.model_response:
            raise ValueError("model_response_required")
        return self
