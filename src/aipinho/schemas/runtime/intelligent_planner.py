from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.services.session.session_store import utc_now


PlannerTaskType = Literal[
    "simple",
    "android",
    "python",
    "multimodal",
    "ocr",
    "vision",
    "coding",
    "debug",
    "review",
    "artifact",
]


class PlannerIntent(AIpinhoModel):
    intent_id: str = Field(default_factory=lambda: f"planner_intent_{uuid4().hex}")
    objective: str
    task_type: PlannerTaskType = "simple"
    complexity: Literal["low", "medium", "high"] = "low"
    requires_graph: bool = True
    requires_review: bool = True
    requires_approval: bool = False
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)


class PlannerTask(AIpinhoModel):
    task_id: str = Field(default_factory=lambda: f"planner_task_{uuid4().hex}")
    objective: str
    workspace: str | None = None
    stack_hint: str | None = None
    requested_actions: list[str] = Field(default_factory=list)
    requested_capabilities: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    policy_snapshot: dict[str, Any] = Field(default_factory=dict)


class ExecutionConstraint(AIpinhoModel):
    constraint_id: str = Field(default_factory=lambda: f"planning_constraint_{uuid4().hex}")
    kind: str
    summary: str
    applies_to: list[str] = Field(default_factory=list)
    blocking: bool = False


class PlanningEvidence(AIpinhoModel):
    evidence_id: str = Field(default_factory=lambda: f"planning_evidence_{uuid4().hex}")
    kind: str
    summary: str
    source: str = "planning_engine"
    confidence: float = 1.0


class PlannerReasoning(AIpinhoModel):
    reasoning_id: str = Field(default_factory=lambda: f"planner_reasoning_{uuid4().hex}")
    question: str
    answer: str
    evidence_ids: list[str] = Field(default_factory=list)


class PlannerNode(AIpinhoModel):
    node_id: str
    executor: str
    runtime_profile: str
    objective: str
    dependencies: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    output_contracts: list[str] = Field(default_factory=list)
    mode: Literal["direct", "delegated", "supervised", "review", "memory", "finalizer"] = "supervised"
    parallel_group: str | None = None
    requires_review: bool = True
    requires_approval: bool = False
    risk_level: Literal["low", "medium", "high"] = "low"
    expected_artifacts: list[str] = Field(default_factory=list)
    estimated_cost: int = 1


class ExecutionStrategy(AIpinhoModel):
    strategy_id: str = Field(default_factory=lambda: f"execution_strategy_{uuid4().hex}")
    name: str
    summary: str
    parallel_groups: list[list[str]] = Field(default_factory=list)
    review_required: bool = True
    approval_required: bool = False
    risk_level: Literal["low", "medium", "high"] = "low"
    estimated_steps: int = 0
    discarded_alternatives: list[str] = Field(default_factory=list)


class PlanningReport(AIpinhoModel):
    report_id: str = Field(default_factory=lambda: f"planning_report_{uuid4().hex}")
    status: Literal["ready", "blocked", "requires_review"] = "ready"
    objective: str
    intent: PlannerIntent
    task: PlannerTask
    strategy: ExecutionStrategy
    nodes: list[PlannerNode] = Field(default_factory=list)
    constraints: list[ExecutionConstraint] = Field(default_factory=list)
    reasoning: list[PlannerReasoning] = Field(default_factory=list)
    evidence: list[PlanningEvidence] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    dependencies: list[dict[str, Any]] = Field(default_factory=list)
    order: list[str] = Field(default_factory=list)
    alternatives_discarded: list[str] = Field(default_factory=list)
    replan_of: str | None = None
    replan_reason: str | None = None
    created_at: str = Field(default_factory=utc_now)
