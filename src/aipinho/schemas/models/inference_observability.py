from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class PromptDiffArtifact(AIpinhoModel):
    original_chars: int = 0
    final_chars: int = 0
    removed_items: list[str] = Field(default_factory=list)
    truncated_items: list[str] = Field(default_factory=list)
    omitted_artifacts: list[str] = Field(default_factory=list)
    omitted_snippets: list[str] = Field(default_factory=list)
    omitted_symbols: list[str] = Field(default_factory=list)


class ContextBudgetArtifact(AIpinhoModel):
    role_limit_chars: int | None = None
    provider_limit_chars: int | None = None
    actual_chars: int = 0
    estimated_tokens: int = 0
    discarded_chars: int = 0
    discarded_items: list[str] = Field(default_factory=list)
    truncated_items: list[str] = Field(default_factory=list)


class CanonicalInferenceInputArtifact(AIpinhoModel):
    artifact_id: str = Field(default_factory=lambda: f"inference_input_{uuid4().hex}")
    role: str | None = None
    operation_type: str | None = None
    semantic_goal: str = ""
    prompt_original: str = ""
    prompt_final: str = ""
    system_prompt: str = ""
    output_schema: dict[str, Any] = Field(default_factory=dict)
    artifacts_used: list[str] = Field(default_factory=list)
    evidence_used: list[str] = Field(default_factory=list)
    diagnosis_ids: list[str] = Field(default_factory=list)
    patch_candidate_id: str | None = None
    symbol_targets: list[str] = Field(default_factory=list)
    file_targets: list[str] = Field(default_factory=list)
    code_snippets: list[dict[str, Any]] = Field(default_factory=list)
    estimated_tokens: int = 0
    prompt_chars: int = 0
    truncated_items: list[str] = Field(default_factory=list)
    context_budget: ContextBudgetArtifact = Field(default_factory=ContextBudgetArtifact)
    provider: str | None = None
    model: str | None = None
    fingerprint: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CanonicalInferenceOutputArtifact(AIpinhoModel):
    artifact_id: str = Field(default_factory=lambda: f"inference_output_{uuid4().hex}")
    input_artifact_id: str | None = None
    raw_output: str = ""
    sanitized_output: str = ""
    parsed_output: dict[str, Any] | list[Any] | str | None = None
    parser: str | None = None
    completion_chars: int = 0
    json_valid: bool | None = None
    retry_count: int = 0
    finish_reason: str = ""
    confidence: float = 0.0
    replacement_detected: bool = False
    replacement_count: int = 0
    empty_output: bool = False
    diagnostics: list[str] = Field(default_factory=list)


class CompletenessAnalysis(AIpinhoModel):
    score: int = 0
    confidence: str = "baixa"
    missing: list[str] = Field(default_factory=list)
    present: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)


class InferenceInputDoctorReport(AIpinhoModel):
    report_id: str = Field(default_factory=lambda: f"inference_input_doctor_{uuid4().hex}")
    status: str = "PASS"
    completeness: CompletenessAnalysis = Field(default_factory=CompletenessAnalysis)
    prompt_diff: PromptDiffArtifact = Field(default_factory=PromptDiffArtifact)
    context_budget: ContextBudgetArtifact = Field(default_factory=ContextBudgetArtifact)
    reason_codes: list[str] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
