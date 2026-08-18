from __future__ import annotations

import json
from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.runtime.execution_plan import CandidatePlan, CanonicalExecutionPlan


ExecutionPlanStatus = Literal["planned", "blocked"]


class ExecutionStage(AIpinhoModel):
    stage_id: str
    stage_type: str
    roles: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    required: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExecutionPlanTrace(AIpinhoModel):
    stage: str
    status: str
    data: dict[str, Any] = Field(default_factory=dict)


class ExecutionPlan(AIpinhoModel):
    plan_id: str = Field(default_factory=lambda: f"execution_plan_{uuid4().hex}")
    status: ExecutionPlanStatus = "planned"
    contract_bundle_id: str
    stages: list[ExecutionStage] = Field(default_factory=list)
    approvals_required: list[str] = Field(default_factory=list)
    artifacts_expected: list[str] = Field(default_factory=list)
    validations_required: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    trace: list[ExecutionPlanTrace] = Field(default_factory=list)
    candidate_plan: CandidatePlan | None = None
    canonical_execution_plan: CanonicalExecutionPlan | None = None


class ExecutionPlanSerializer:
    @staticmethod
    def to_json(plan: ExecutionPlan) -> str:
        return json.dumps(plan.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)

    @staticmethod
    def from_json(payload: str) -> ExecutionPlan:
        return ExecutionPlan.model_validate_json(payload)
