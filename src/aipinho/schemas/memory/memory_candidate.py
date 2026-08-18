from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

MemoryCandidateKind = Literal[
    "architecture_decision",
    "policy_decision",
    "validation_learning",
    "bug_fix_summary",
    "patch_outcome",
    "runtime_behavior",
    "project_constraint",
    "user_instruction",
    "operational_procedure",
    "known_limitation",
    "testing_guidance",
    "risk_pattern",
    "design_rationale",
]
MemoryCandidateStatus = Literal["candidate", "needs_review", "blocked", "rejected", "duplicate"]
MemoryCandidateRiskLevel = Literal["low", "medium", "high", "critical"]
MemoryCandidateConfidence = Literal["low", "medium", "high"]
DedupeStatus = Literal["unique", "duplicate", "near_duplicate"]
SensitivityStatus = Literal["safe", "needs_redaction", "blocked"]


class MemoryCandidateSource(AIpinhoModel):
    source_type: str
    source_id: str | None = None
    source_ref: str | None = None
    source_payload: dict[str, Any] = Field(default_factory=dict)
    trusted: bool = False


class MemoryCandidateEvidence(AIpinhoModel):
    evidence_id: str
    evidence_type: str
    source_ref: str
    summary: str
    path: str | None = None
    line_start: int | None = None
    line_end: int | None = None


class MemoryCandidateScope(AIpinhoModel):
    scope_type: str
    workspace: str | None = None
    module: str | None = None
    service: str | None = None
    policy: str | None = None
    reason: str | None = None


class MemoryCandidateRisk(AIpinhoModel):
    level: MemoryCandidateRiskLevel = "medium"
    reasons: list[str] = Field(default_factory=list)
    approval_future_required: bool = False


class MemoryCandidateValidation(AIpinhoModel):
    status: str
    passed: bool
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class MemoryCandidateDedupe(AIpinhoModel):
    status: DedupeStatus = "unique"
    normalized_hash: str
    kind_scope_hash: str
    matched_candidate_id: str | None = None
    similarity: float = 0.0


class MemoryCandidateConflict(AIpinhoModel):
    has_conflict: bool = False
    conflict_candidate_ids: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class MemoryCandidateTrace(AIpinhoModel):
    stage: str
    status: str
    reason: str
    data: dict[str, Any] = Field(default_factory=dict)


class MemoryCandidateEvent(AIpinhoModel):
    event_id: str
    candidate_id: str
    event_type: str
    status: str
    message: str
    created_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryCandidateAudit(AIpinhoModel):
    candidate_id: str
    created_at: str
    source_type: str
    candidate_only: bool = True
    approved_memory_written: bool = False
    vectorstore_written: bool = False
    embeddings_generated: bool = False
    raw_logs_stored: bool = False
    secrets_stored: bool = False


class MemoryCandidateRequest(AIpinhoModel):
    text: str
    summary: str | None = None
    kind: str | None = None
    source: MemoryCandidateSource | None = None
    scope: MemoryCandidateScope | None = None
    evidence: list[MemoryCandidateEvidence] = Field(default_factory=list)
    status: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryCandidate(AIpinhoModel):
    candidate_id: str
    status: MemoryCandidateStatus
    kind: MemoryCandidateKind
    text: str
    summary: str
    source: MemoryCandidateSource
    scope: MemoryCandidateScope
    evidence: list[MemoryCandidateEvidence] = Field(default_factory=list)
    confidence: MemoryCandidateConfidence = "low"
    risk: MemoryCandidateRisk = Field(default_factory=MemoryCandidateRisk)
    validation: MemoryCandidateValidation = Field(default_factory=lambda: MemoryCandidateValidation(status="blocked", passed=False))
    dedupe: MemoryCandidateDedupe
    conflict: MemoryCandidateConflict = Field(default_factory=MemoryCandidateConflict)
    trace: list[MemoryCandidateTrace] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str


class MemoryCandidateResult(AIpinhoModel):
    status: str
    candidate: MemoryCandidate | None = None
    warnings: list[str] = Field(default_factory=list)
    approved_memory_enabled: bool = False
    vectorstore_enabled: bool = False
    embeddings_enabled: bool = False
    rag_enabled: bool = False


class MemoryExtractionResult(AIpinhoModel):
    status: str
    source: MemoryCandidateSource
    candidates: list[MemoryCandidate] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    candidate_only: bool = True
    approved_memory_enabled: bool = False
    vectorstore_enabled: bool = False
    embeddings_enabled: bool = False
    rag_enabled: bool = False
