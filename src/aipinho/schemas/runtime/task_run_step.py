from __future__ import annotations
from typing import Any
from pydantic import Field
from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.runtime.task_run_state import TaskRunStepStatus
from aipinho.schemas.runtime.task_run_trace import TaskRunTraceItem

class TaskRunStep(AIpinhoModel):
    step_id: str
    step_type: str
    action: str
    required: bool = True
    side_effect: bool = False
    status: TaskRunStepStatus = "pending"
    input_summary: dict[str, Any] = Field(default_factory=dict)
    output_summary: dict[str, Any] = Field(default_factory=dict)
    started_at: str | None = None
    finished_at: str | None = None
    warnings: list[str] = Field(default_factory=list)
    violations: list[str] = Field(default_factory=list)
    trace: list[TaskRunTraceItem] = Field(default_factory=list)
