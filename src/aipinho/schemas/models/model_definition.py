from __future__ import annotations

from typing import Any

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.models.generation_config import GenerationConfig


class ModelDefinition(AIpinhoModel):
    model_id: str
    provider_id: str
    display_name: str
    enabled: bool = False
    local: bool = True
    real_inference: bool = False
    default: bool = False
    manual_only: bool = False
    default_coding_candidate: bool = False
    requires_operator_confirmation: bool = False
    latency_warning_required: bool = False
    requires_mmproj: bool = False
    experimental_until_doctor_passed: bool = False
    modality: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    family: str | None = None
    parameter_class: str | None = None
    quantization: str | None = None
    hardware_class: str | None = None
    context_window_tokens: int = 4096
    max_output_tokens: int = 512
    default_generation_config: GenerationConfig = Field(default_factory=GenerationConfig)
    roles: list[str] = Field(default_factory=list)
    future_roles: list[str] = Field(default_factory=list)
    model_path: str | None = None
    mmproj_path: str | None = None
    file_size_bytes: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def is_runtime_model(self) -> bool:
        return bool(self.local and self.model_path)
