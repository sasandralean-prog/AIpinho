from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


ExecutionPlanStatus = Literal["candidate", "ready", "blocked", "approved", "executing", "completed", "failed", "cancelled"]


class CanonicalExecutionStep(AIpinhoModel):
    step_id: str
    step_type: str
    action: str
    required: bool = True
    side_effect: bool = False
    depends_on: list[str] = Field(default_factory=list)
    inputs: dict[str, Any] = Field(default_factory=dict)
    expected_outputs: list[str] = Field(default_factory=list)
    required_capabilities: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CandidatePlan(AIpinhoModel):
    candidate_plan_id: str = Field(default_factory=lambda: f"candidate_plan_{uuid4().hex}")
    semantic_goal: str
    operation_kind: str
    workspace: dict[str, Any] = Field(default_factory=dict)
    targets: list[str] = Field(default_factory=list)
    dependencies: list[dict[str, Any]] = Field(default_factory=list)
    requested_actions: list[str] = Field(default_factory=list)
    required_capabilities: list[str] = Field(default_factory=list)
    execution_steps: list[CanonicalExecutionStep] = Field(default_factory=list)
    rollback_strategy: dict[str, Any] = Field(default_factory=dict)
    validation_requirements: list[str] = Field(default_factory=list)
    artifact_expectations: list[str] = Field(default_factory=list)
    trace_id: str = Field(default_factory=lambda: f"trace_{uuid4().hex}")
    source_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CanonicalExecutionPlan(AIpinhoModel):
    execution_id: str = Field(default_factory=lambda: f"execution_{uuid4().hex}")
    candidate_plan_id: str | None = None
    task_id: str | None = None
    taskrun_id: str | None = None
    semantic_goal: str
    operation_kind: str
    workspace: dict[str, Any] = Field(default_factory=dict)
    targets: list[str] = Field(default_factory=list)
    dependencies: list[dict[str, Any]] = Field(default_factory=list)
    policy_snapshot: dict[str, Any] = Field(default_factory=dict)
    approval_required: bool = False
    approval_id: str | None = None
    execution_steps: list[CanonicalExecutionStep] = Field(default_factory=list)
    rollback_strategy: dict[str, Any] = Field(default_factory=dict)
    validation_requirements: list[str] = Field(default_factory=list)
    artifact_expectations: list[str] = Field(default_factory=list)
    required_capabilities: list[str] = Field(default_factory=list)
    trace_id: str
    status: ExecutionPlanStatus = "ready"
    blocked_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ExecutionPlanPromotionDecision(AIpinhoModel):
    status: Literal["promoted", "rejected"]
    candidate_plan_id: str
    execution_plan: CanonicalExecutionPlan | None = None
    reason_codes: list[str] = Field(default_factory=list)
    policy_snapshot: dict[str, Any] = Field(default_factory=dict)
    trace: list[dict[str, Any]] = Field(default_factory=list)


class CanonicalExecutionPlanSerializer:
    @staticmethod
    def to_json(plan: CanonicalExecutionPlan) -> str:
        return json.dumps(plan.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)

    @staticmethod
    def from_json(payload: str) -> CanonicalExecutionPlan:
        return CanonicalExecutionPlan.model_validate_json(payload)
