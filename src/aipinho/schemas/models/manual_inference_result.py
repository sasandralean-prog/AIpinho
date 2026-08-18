from __future__ import annotations

from typing import Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

ManualInferenceStatus = Literal["completed", "completed_with_warning", "blocked", "unavailable", "timeout", "failed", "degraded"]


class ExpectedOutputCheck(AIpinhoModel):
    enabled: bool = True
    passed: bool = False
    expected_contains_any: list[str] = Field(default_factory=list)
    reason: str | None = None


class ManualInferenceResult(AIpinhoModel):
    run_id: str = Field(default_factory=lambda: f"manual_run_{uuid4().hex}")
    status: ManualInferenceStatus = "blocked"
    profile_id: str = "llama_cpp_smoke"
    model_id: str = "llama.local.placeholder"
    provider_id: str = "llama_cpp.local"
    real_inference: bool = False
    process_started: bool = False
    duration_ms: int = 0
    output_preview: str = ""
    expected_output_check: ExpectedOutputCheck = Field(default_factory=ExpectedOutputCheck)
    model_response: dict[str, object] = Field(default_factory=dict)
    gate_decision: dict[str, object] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    violations: list[str] = Field(default_factory=list)
    audit_event_id: str | None = None
    trace: list[dict[str, object]] = Field(default_factory=list)
