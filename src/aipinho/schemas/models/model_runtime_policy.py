from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class ModelRuntimePolicy(AIpinhoModel):
    chat_auto_use_enabled: bool = False
    role_pipeline_auto_use_enabled: bool = False
    first_token_probe_enabled_by_default: bool = False
    tool_calling_enabled: bool = False
    network_download_enabled: bool = False
    max_auto_parameter_class: str = "7b"
    manual_only_parameter_classes: list[str] = Field(default_factory=list)
