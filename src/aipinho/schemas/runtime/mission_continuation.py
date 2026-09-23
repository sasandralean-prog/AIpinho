from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.runtime.mission_contract import MissionContract
from aipinho.schemas.runtime.phase_dependency_evaluation import (
    DownstreamPhaseRequirements,
    PhaseDependencyEvaluation,
)


MissionContinuationAction = Literal[
    "continue_to_next_phase",
    "await_existing_authority",
    "request_new_authority",
    "block",
    "complete",
]


class MissionContinuationCandidate(AIpinhoModel):
    candidate_id: str = Field(default_factory=lambda: f"mission_continuation_candidate_{uuid4().hex}")
    planner_ref: str
    dependency_id: str
    phase_id: str
    operation_type: str
    contract_type: str
    runtime_profile: str | None = None
    requested_actions: list[str] = Field(default_factory=list)
    required_capabilities: list[str] = Field(default_factory=list)
    runtime_capabilities_required: list[str] = Field(default_factory=list)
    local_resource_ids: list[str] = Field(default_factory=list)
    remote_resource_ids: list[str] = Field(default_factory=list)
    workspace_resource_id: str | None = None
    mode: str = "governed"
    semantic_goal: str | None = None
    requirements: DownstreamPhaseRequirements
    metadata: dict[str, Any] = Field(default_factory=dict)


class MissionContinuationPlanningResult(AIpinhoModel):
    status: Literal["planned", "not_applicable", "blocked"]
    reason_code: str
    candidate: MissionContinuationCandidate | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)
    trace: list[dict[str, Any]] = Field(default_factory=list)


class MissionContinuationDecision(AIpinhoModel):
    action: MissionContinuationAction
    reason_code: str
    mission_id: str | None = None
    strategy: str | None = None
    previous_run_id: str | None = None
    previous_phase: str | None = None
    next_phase: str | None = None
    candidate_id: str | None = None
    planner_ref: str | None = None
    child_contract: MissionContract | None = None
    dependency_evaluation: PhaseDependencyEvaluation | None = None
    authority_gap: list[str] = Field(default_factory=list)
    outstanding_completion_requirements: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    trace: list[dict[str, Any]] = Field(default_factory=list)


class MissionContinuationMaterialization(AIpinhoModel):
    status: Literal["materialized", "not_applicable", "blocked"]
    reason_code: str
    decision: MissionContinuationDecision
    child_task_run_id: str | None = None
    child_task_id: str | None = None
    child_operation_id: str | None = None
    child_phase: str | None = None
    reused_existing_child: bool = False
    dependency_evaluation: PhaseDependencyEvaluation | None = None
    dependency_admission: dict[str, Any] | None = None
    evidence_refs: list[str] = Field(default_factory=list)


class MissionContinuationExecution(AIpinhoModel):
    status: Literal["executed", "not_applicable", "blocked"]
    reason_code: str
    materialization: MissionContinuationMaterialization
    child_task_run_id: str | None = None
    child_status: str | None = None
    result_status: str | None = None
    reused_terminal_result: bool = False
    evidence_refs: list[str] = Field(default_factory=list)
