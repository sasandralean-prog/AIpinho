from __future__ import annotations
from typing import Any
from pydantic import Field
from aipinho.schemas.common.base import AIpinhoModel

class TaskRuntimeStatus(AIpinhoModel):
    status: str = "ok"
    enabled: bool = True
    mode: str = "read_only"
    write_enabled: bool = False
    patch_enabled: bool = False
    shell_enabled: bool = False
    git_write_enabled: bool = False
    rag_enabled: bool = False
    memory_write_enabled: bool = False
    background_execution: bool = False
    real_model_auto_use: bool = False
    model_tool_calling_enabled: bool = False
    allowed_actions: list[str] = Field(default_factory=list)
    configs: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    validation_gate_enabled: bool = False
    report_quality_gate_enabled: bool = False
    side_effect_validation_enabled: bool = False

