from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.services.session.session_store import utc_now

ExecutionNodeStatus = Literal[
    "pending",
    "ready",
    "waiting",
    "running",
    "completed",
    "partial",
    "blocked",
    "failed",
    "cancelled",
    "skipped",
    "timeout",
]
ExecutionGraphStatus = Literal[
    "created",
    "ready",
    "waiting",
    "running",
    "completed",
    "partial",
    "blocked",
    "failed",
    "cancelled",
    "timeout",
]
ExecutionGraphType = Literal["task_plan", "cooperative"]


class ExecutionEdge(AIpinhoModel):
    edge_id: str = Field(default_factory=lambda: f"edge_{uuid4().hex}")
    from_node_id: str
    to_node_id: str
    reason: str
    required: bool = True


class ExecutionDependency(AIpinhoModel):
    dependency_id: str = Field(default_factory=lambda: f"dependency_{uuid4().hex}")
    source_node_id: str
    target_node_id: str
    dependency_type: str = "output_contract"
    required: bool = True
    status: Literal["pending", "completed", "blocked"] = "pending"
    output_contract: str | None = None


class NodeRuntime(AIpinhoModel):
    runtime_id: str = Field(default_factory=lambda: f"node_runtime_{uuid4().hex}")
    profile: str
    executor: str
    execution_mode: Literal["direct", "delegated", "supervised", "review", "memory", "finalizer"] = "supervised"
    allowed_capabilities: list[str] = Field(default_factory=list)
    source_authority: str = "aipinho"
    poll_endpoint: str | None = None
    retry_policy: dict[str, Any] = Field(default_factory=lambda: {"mode": "retry_node", "max_retries": 2})


class ExecutionResult(AIpinhoModel):
    result_id: str = Field(default_factory=lambda: f"node_result_{uuid4().hex}")
    node_id: str | None = None
    status: str
    output_contract: str | None = None
    outputs: dict[str, Any] = Field(default_factory=dict)
    artifact_refs: list[dict[str, Any]] = Field(default_factory=list)
    memory_candidates: list[dict[str, Any]] = Field(default_factory=list)
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    speakertruth: dict[str, Any] = Field(default_factory=dict)
    review: dict[str, Any] = Field(default_factory=dict)
    validation: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now)


class ExecutionMetrics(AIpinhoModel):
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: int | None = None
    attempts: int = 0
    warnings_count: int = 0
    violations_count: int = 0


class ExecutionCheckpoint(AIpinhoModel):
    checkpoint_id: str = Field(default_factory=lambda: f"checkpoint_{uuid4().hex}")
    node_id: str | None = None
    status: str
    summary: str
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)


class ExecutionLifecycle(AIpinhoModel):
    status: ExecutionGraphStatus = "created"
    current_node_id: str | None = None
    completed_node_ids: list[str] = Field(default_factory=list)
    blocked_node_ids: list[str] = Field(default_factory=list)
    failed_node_ids: list[str] = Field(default_factory=list)
    cancelled_node_ids: list[str] = Field(default_factory=list)
    updated_at: str = Field(default_factory=utc_now)


class ExecutionContext(AIpinhoModel):
    run_id: str
    workspace: str | None = None
    contract_type: str | None = None
    operation_type: str | None = None
    runtime_profile: str | None = None
    requested_actions: list[str] = Field(default_factory=list)
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)


class ExecutionNode(AIpinhoModel):
    node_id: str
    step_id: str | None = None
    objective: str
    worker: str
    executor: str | None = None
    runtime_profile: str | None = None
    runtime: NodeRuntime | None = None
    dependencies: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    contracts: list[str] = Field(default_factory=list)
    artifacts_expected: list[str] = Field(default_factory=list)
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    memory_candidates: list[dict[str, Any]] = Field(default_factory=list)
    speakertruth: dict[str, Any] = Field(default_factory=dict)
    review: dict[str, Any] = Field(default_factory=dict)
    approval: dict[str, Any] = Field(default_factory=dict)
    validation_gate: dict[str, Any] = Field(default_factory=dict)
    rollback: dict[str, Any] = Field(default_factory=dict)
    action: str | None = None
    side_effect: bool = False
    required: bool = True
    status: ExecutionNodeStatus = "pending"
    metrics: ExecutionMetrics = Field(default_factory=ExecutionMetrics)
    output_summary: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    violations: list[str] = Field(default_factory=list)
    retry_count: int = 0


class ExecutionGraph(AIpinhoModel):
    graph_id: str = Field(default_factory=lambda: f"exec_graph_{uuid4().hex}")
    run_id: str
    graph_type: ExecutionGraphType = "task_plan"
    status: ExecutionGraphStatus = "created"
    context: ExecutionContext
    nodes: list[ExecutionNode] = Field(default_factory=list)
    edges: list[ExecutionEdge] = Field(default_factory=list)
    dependencies: list[ExecutionDependency] = Field(default_factory=list)
    results: list[ExecutionResult] = Field(default_factory=list)
    checkpoints: list[ExecutionCheckpoint] = Field(default_factory=list)
    lifecycle: ExecutionLifecycle = Field(default_factory=ExecutionLifecycle)
    metrics: ExecutionMetrics = Field(default_factory=ExecutionMetrics)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    memory_candidates: list[dict[str, Any]] = Field(default_factory=list)
    speakertruth: dict[str, Any] = Field(default_factory=dict)
    review: dict[str, Any] = Field(default_factory=dict)
    supervisor: dict[str, Any] = Field(default_factory=dict)
    planning_report: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)
    warnings: list[str] = Field(default_factory=list)


class ExecutionResume(AIpinhoModel):
    graph_id: str
    run_id: str
    ready_node_ids: list[str] = Field(default_factory=list)
    blocked_node_ids: list[str] = Field(default_factory=list)
    completed_node_ids: list[str] = Field(default_factory=list)
    status: ExecutionGraphStatus


class ExecutionCancel(AIpinhoModel):
    graph_id: str
    run_id: str
    reason: str
    cancelled_node_ids: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)
