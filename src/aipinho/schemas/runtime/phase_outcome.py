from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


class PhaseOutcome(AIpinhoModel):
    """Canonical, rebuildable projection of a terminal phase result.

    Presence means only that an upstream phase reached a durable outcome.
    It never grants downstream execution authority.
    """

    outcome_id: str = Field(default_factory=lambda: f"phase_outcome_{uuid4().hex}")
    producer_task_run_id: str
    producer_operation_id: str | None = None
    session_id: str | None = None
    phase_id: str
    workspace: str | None = None
    runtime_status: str
    result_status: str
    reason_code: str | None = None
    semantic_completion: dict[str, Any] = Field(default_factory=dict)
    phase_dependency: dict[str, Any] = Field(default_factory=dict)
    use_safety: dict[str, Any] = Field(default_factory=dict)
    semantic_properties: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    required_disclosures: list[str] = Field(default_factory=list)
    missing_truth: list[str] = Field(default_factory=list)
    risk_constraints: list[str] = Field(default_factory=list)
    artifact_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    result_ref: str
    authority_refs: list[str] = Field(default_factory=list)
    authority_sha256: str
    projected_at: str = Field(default_factory=utc_now_iso)
    schema_version: str = "phase_outcome.v1"
