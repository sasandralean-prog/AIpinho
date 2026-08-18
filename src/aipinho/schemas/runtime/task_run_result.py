from __future__ import annotations
from typing import Any, Literal
from pydantic import Field
from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.runtime.task_block_cause import TaskBlockCause
from aipinho.schemas.runtime.task_completion import TaskCompletionEvaluation

class TaskRunResult(AIpinhoModel):
    run_id: str
    status: Literal["completed", "completed_with_limitations", "partial", "failed", "cancelled", "blocked"]
    summary: str
    source: str | None = None
    reason_code: str | None = None
    finished_at: str | None = None
    outputs: dict[str, Any] = Field(default_factory=dict)
    step_summaries: list[dict[str, Any]] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    blocked_items: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    events_count: int = 0
    trace_ref: str | None = None
    safe_to_display: bool = True
    validation: dict[str, Any] | None = None
    block_cause: TaskBlockCause | None = None
    completion: TaskCompletionEvaluation | None = None

