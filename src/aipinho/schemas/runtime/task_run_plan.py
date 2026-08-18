from __future__ import annotations
from typing import Any
from pydantic import Field
from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.runtime.execution_plan import CandidatePlan, CanonicalExecutionPlan
from aipinho.schemas.runtime.task_run_step import TaskRunStep
from aipinho.schemas.runtime.task_run_trace import TaskRunTraceItem

class TaskRunPlan(AIpinhoModel):
    plan_id: str
    contract_type: str
    status: str = "ready"
    steps: list[TaskRunStep] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    trace: list[TaskRunTraceItem] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    candidate_plan: CandidatePlan | None = None
    canonical_execution_plan: CanonicalExecutionPlan | None = None
