from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class ManualInferenceRequester(AIpinhoModel):
    type: str = "user"
    id: str = "local_operator"


class ManualInferenceRequest(AIpinhoModel):
    profile_id: str = "llama_cpp_smoke"
    model_id: str = "llama.local.placeholder"
    provider_id: str = "llama_cpp.local"
    prompt_id: str | None = "smoke_minimal_pt"
    custom_prompt: str | None = None
    allow_real_inference: bool = False
    operator_confirmed: bool = False
    include_trace: bool = False
    requested_by: ManualInferenceRequester = Field(default_factory=ManualInferenceRequester)
    metadata: dict[str, object] = Field(default_factory=dict)
