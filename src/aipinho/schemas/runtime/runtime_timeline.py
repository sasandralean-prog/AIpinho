from __future__ import annotations

from typing import Any

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class RuntimeTimelineEvent(AIpinhoModel):
    event_id: str
    sequence: int
    timestamp: str
    task_id: str | None = None
    task_run_id: str
    phase: str | None = None
    runtime_step: str | None = None
    event_type: str
    status: str
    message: str = ""
    duration_ms: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuntimeTimelineStep(AIpinhoModel):
    step_id: str
    step_type: str
    action: str
    status: str
    start_event_id: str | None = None
    finish_event_id: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: int | None = None
    artifacts: list[str] = Field(default_factory=list)
    validations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    violations: list[str] = Field(default_factory=list)
    complete: bool = False
    gap_reasons: list[str] = Field(default_factory=list)


class RuntimeTimelineArtifact(AIpinhoModel):
    artifact_id: str
    logical_path: str | None = None
    artifact_type: str | None = None
    producer_step: str | None = None
    event_id: str | None = None
    task_id: str | None = None
    task_run_id: str | None = None
    validation_status: str | None = None
    status: str | None = None
    storage_ref: str | None = None
    orphan: bool = False
    orphan_reasons: list[str] = Field(default_factory=list)


class RuntimeTimelineValidation(AIpinhoModel):
    validation_id: str | None = None
    event_id: str | None = None
    validator: str = "task_run_validation_gate"
    status: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)


class RuntimeTimelineCompletion(AIpinhoModel):
    status: str
    source: str = "timeline"
    safe_to_report_success: bool = False
    terminal_event_id: str | None = None
    missing_outputs: list[str] = Field(default_factory=list)
    derived_from_event_ids: list[str] = Field(default_factory=list)


class RuntimeTimeline(AIpinhoModel):
    timeline_id: str
    task_id: str | None = None
    task_run_id: str
    operation_id: str | None = None
    workspace_id: str | None = None
    project_id: str | None = None
    status: str
    phase: str | None = None
    events: list[RuntimeTimelineEvent] = Field(default_factory=list)
    steps: list[RuntimeTimelineStep] = Field(default_factory=list)
    artifacts: list[RuntimeTimelineArtifact] = Field(default_factory=list)
    validations: list[RuntimeTimelineValidation] = Field(default_factory=list)
    completion: RuntimeTimelineCompletion
    gaps: list[str] = Field(default_factory=list)
    orphan_event_ids: list[str] = Field(default_factory=list)
    orphan_artifact_ids: list[str] = Field(default_factory=list)
    sequence_contiguous: bool = True
    observable: bool = True
    speaker_truth_evidence: dict[str, Any] = Field(default_factory=dict)

