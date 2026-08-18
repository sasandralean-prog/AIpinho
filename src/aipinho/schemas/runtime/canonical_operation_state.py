from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

CanonicalOperationStatus = Literal[
    "CREATED",
    "READY",
    "RUNNING",
    "WAITING_APPROVAL",
    "WAITING_ARTIFACTS",
    "VALIDATING",
    "COMPLETED",
    "FAILED",
    "BLOCKED",
    "CANCELLED",
]


class CanonicalOperationState(AIpinhoModel):
    """Single runtime state consumed by completion, truth and UI layers."""

    status: CanonicalOperationStatus = "CREATED"
    task_id: str | None = None
    task_run_id: str | None = None
    operation_id: str | None = None
    lifecycle_status: str | None = None
    validation_status: str | None = None
    completion_status: str | None = None
    speaker_truth_status: str | None = None
    ui_status: str | None = None
    safe_to_report_success: bool = False
    missing_outputs: list[str] = Field(default_factory=list)
    missing_artifacts: list[str] = Field(default_factory=list)
    reason_code: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    source: str = "canonical_operation_state_service"
