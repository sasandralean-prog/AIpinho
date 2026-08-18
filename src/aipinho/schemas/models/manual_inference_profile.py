from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class ManualInferenceProfile(AIpinhoModel):
    profile_id: str
    enabled: bool = False
    provider_id: str = "llama_cpp.local"
    model_id: str = "llama.local.placeholder"
    real_inference: bool = True
    manual_only: bool = True
    allow_chat_auto_use: bool = False
    allow_report_auto_use: bool = False
    allow_analysis_auto_use: bool = False
    require_request_opt_in: bool = True
    require_operator_confirmation: bool = True
    timeout_seconds: int = 20
    max_input_chars: int = 1000
    max_output_tokens: int = 64
    ctx_size: int = 1024
    temperature: float = 0.0
    top_p: float = 1.0
    threads: int | None = None
    prompt_id: str | None = None
    output_contract_type: str = "plain_text"
    safety_envelope_id: str = "local_smoke_test"
    notes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
