from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


EvidenceKind = Literal[
    "task_run",
    "task_run_plan",
    "execution_graph",
    "execution_node",
    "operational_memory",
    "policy_snapshot",
    "worker_contract",
    "validation_result",
    "artifact",
    "trace",
]
EvidenceStrength = Literal["weak", "medium", "strong"]
EvidenceScoreStatus = Literal["insufficient", "partial", "sufficient"]
DecisionAuditStatus = Literal["passed", "failed"]


class EvidenceItem(AIpinhoModel):
    evidence_id: str = Field(default_factory=lambda: f"evidence_{uuid4().hex}")
    kind: EvidenceKind
    source_id: str
    source_ref: str | None = None
    summary: str
    strength: EvidenceStrength = "medium"
    created_at: str = Field(default_factory=utc_now_iso)
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class EvidenceIndex(AIpinhoModel):
    index_id: str = Field(default_factory=lambda: f"evidence_index_{uuid4().hex}")
    evidence: list[EvidenceItem] = Field(default_factory=list)
    by_kind: dict[str, list[str]] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now_iso)


class EvidenceScore(AIpinhoModel):
    score_id: str = Field(default_factory=lambda: f"evidence_score_{uuid4().hex}")
    status: EvidenceScoreStatus
    score: float
    evidence_count: int
    strong_count: int = 0
    medium_count: int = 0
    weak_count: int = 0
    missing_required_kinds: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class EvidenceReasoning(AIpinhoModel):
    reasoning_id: str = Field(default_factory=lambda: f"evidence_reasoning_{uuid4().hex}")
    status: EvidenceScoreStatus
    summary: str
    required_kinds: list[str] = Field(default_factory=list)
    present_kinds: list[str] = Field(default_factory=list)
    missing_kinds: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class EvidenceBackedDecision(AIpinhoModel):
    decision_id: str = Field(default_factory=lambda: f"evidence_decision_{uuid4().hex}")
    subject: str
    decision: str
    status: Literal["proposed", "accepted", "blocked"] = "proposed"
    evidence_index_id: str
    evidence_score: EvidenceScore
    reasoning: EvidenceReasoning
    evidence_ids: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)


class DecisionAudit(AIpinhoModel):
    audit_id: str = Field(default_factory=lambda: f"decision_audit_{uuid4().hex}")
    decision_id: str
    status: DecisionAuditStatus
    reason: str
    evidence_score: float
    evidence_count: int
    missing_required_kinds: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)
