from __future__ import annotations

from typing import Any

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class RuntimeTruthEvidence(AIpinhoModel):
    evidence_type: str
    evidence_id: str | None = None
    status: str | None = None
    summary: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuntimeTruth(AIpinhoModel):
    truth_id: str
    task_id: str | None = None
    task_run_id: str
    status: str
    phase: str = "unknown"
    reason_code: str = ""
    safe_to_report_success: bool = False
    runtime_status: str | None = None
    workflow_status: str | None = None
    completion_status: str | None = None
    validation_status: str | None = None
    timeline_status: str | None = None
    semantic_truth_status: str | None = None
    semantic_truth_safe_to_report_success: bool | None = None
    semantic_truth_reason_codes: list[str] = Field(default_factory=list)
    semantic_truth_disclosures: list[str] = Field(default_factory=list)
    semantic_graph_id: str | None = None
    semantic_graph_authority_sha256: str | None = None
    semantic_truth_facet_id: str | None = None
    semantic_truth_facet_authority_sha256: str | None = None
    mission_id: str | None = None
    mission_completion_status: str | None = None
    mission_completion_safe_to_report_success: bool | None = None
    mission_completion_reason_codes: list[str] = Field(default_factory=list)
    mission_completion_disclosures: list[str] = Field(default_factory=list)
    mission_completion_authority_sha256: str | None = None
    ui_status: str
    speaker_truth_status: str
    evidence: list[RuntimeTruthEvidence] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    source: str = "runtime_truth_engine"
