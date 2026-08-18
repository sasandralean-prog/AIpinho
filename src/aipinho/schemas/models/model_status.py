from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class ModelStatus(AIpinhoModel):
    status: str
    default_model: str = "stub.default"
    real_inference_enabled: bool = False
    models_registered: int = 0
    registered_local_models: int = 0
    compat_models_registered: int = 0
    providers_registered: int = 0
    enabled_models: list[str] = Field(default_factory=list)
    enabled_providers: list[str] = Field(default_factory=list)
    default_coding_candidate: str | None = None
    chat_model_use_enabled: bool = False
    role_model_use_enabled: bool = False
    warnings: list[str] = Field(default_factory=list)
