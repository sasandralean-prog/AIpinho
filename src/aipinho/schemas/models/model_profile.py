from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class ModelProfile(AIpinhoModel):
    model_id: str
    provider_id: str
    display_name: str
    hardware_class: str | None = None
    parameter_class: str | None = None
    quantization: str | None = None
    manual_only: bool = False
    default: bool = False
    default_coding_candidate: bool = False
    path_configured: bool = False
    file_exists: bool = False
    size_bytes: int | None = None
    capabilities: list[str] = Field(default_factory=list)
    modality: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
