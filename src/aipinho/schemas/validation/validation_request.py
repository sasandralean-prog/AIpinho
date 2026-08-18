from __future__ import annotations
from typing import Any, Literal
from pydantic import Field
from aipinho.schemas.common.base import AIpinhoModel

ValidationTargetType = Literal["task_run", "task_result", "project_report", "role_pipeline_run", "side_effects", "evidence", "context_usage"]

class ValidationRequest(AIpinhoModel):
    target_type: ValidationTargetType
    target_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    include_trace: bool = False
