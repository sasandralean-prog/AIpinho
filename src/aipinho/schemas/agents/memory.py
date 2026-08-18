from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


MemoryNamespace = Literal[
    "memory:aipinho",
    "memory:lucio",
    "memory:codex",
    "memory:gemini",
    "memory:shared",
    "memory:project",
    "memory:regression",
    "memory:user_preferences",
    "memory:security",
]
MemoryScope = Literal["private", "shared", "project", "regression", "user_preference", "security"]
MemoryType = Literal[
    "fact",
    "decision",
    "preference",
    "project_context",
    "architecture_context",
    "bug",
    "regression_candidate",
    "command",
    "artifact_reference",
    "validation_result",
    "policy_note",
    "summary",
    "warning",
    "security_note",
    "security_lesson",
    "bug_pattern",
    "fix_pattern",
    "validation_lesson",
    "ux_lesson",
    "policy_lesson",
    "prompt_routing_lesson",
    "quality_gate_lesson",
    "workflow_lesson",
    "model_runtime_lesson",
    "architecture_decision",
]
MemorySourceType = Literal[
    "user_explicit",
    "agent_summary",
    "tool_evidence",
    "validation_evidence",
    "report",
    "artifact",
    "event_trace",
    "manual_import",
    "system_inferred",
]
MemoryValidationStatus = Literal["unvalidated", "candidate", "validated", "contradicted", "stale", "superseded", "rejected"]
MemoryConfidence = Literal["low", "medium", "high", "confirmed"]
MemoryFreshness = Literal["fresh", "recent", "aging", "stale", "unknown"]
MemoryAccessType = Literal["read", "write", "update", "delete", "validate", "supersede", "reject"]
MemoryCandidateStatus = Literal["pending", "accepted", "rejected", "merged", "superseded"]
MemoryPolicyDecision = Literal["allow", "deny", "require_validation", "candidate_only"]


class MemoryRecord(AIpinhoModel):
    memory_id: str = Field(default_factory=lambda: f"agent_memory_{uuid4().hex}")
    namespace: MemoryNamespace
    agent_id: str | None = None
    scope: MemoryScope
    title: str
    content_sanitized: str
    memory_type: MemoryType
    source_type: MemorySourceType
    source_ref: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: MemoryConfidence = "low"
    freshness: MemoryFreshness = "unknown"
    validation_status: MemoryValidationStatus = "unvalidated"
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    expires_at: str | None = None
    tags: list[str] = Field(default_factory=list)
    project_id: str | None = None
    workspace_id: str | None = None
    supersedes: str | None = None
    superseded_by: str | None = None
    contradiction_refs: list[str] = Field(default_factory=list)
    access_policy: dict[str, Any] = Field(default_factory=dict)
    write_policy: dict[str, Any] = Field(default_factory=dict)
    raw_ref: str | None = None
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class MemoryCandidate(AIpinhoModel):
    candidate_id: str = Field(default_factory=lambda: f"agent_memory_candidate_{uuid4().hex}")
    proposed_by_agent_id: str
    namespace: MemoryNamespace
    scope: MemoryScope
    title: str
    content_sanitized: str
    memory_type: MemoryType
    source_ref: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: MemoryConfidence = "low"
    reason_to_remember: str = ""
    proposed_at: str = Field(default_factory=utc_now_iso)
    status: MemoryCandidateStatus = "pending"
    reviewed_by: str | None = None
    memory_id: str | None = None
    warnings: list[str] = Field(default_factory=list)
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class MemoryAccessLog(AIpinhoModel):
    access_id: str = Field(default_factory=lambda: f"agent_memory_access_{uuid4().hex}")
    memory_id: str | None = None
    candidate_id: str | None = None
    agent_id: str
    session_id: str | None = None
    run_id: str | None = None
    access_type: MemoryAccessType
    reason: str
    policy_decision_id: str | None = None
    created_at: str = Field(default_factory=utc_now_iso)
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class MemoryNamespaceInfo(AIpinhoModel):
    namespace: MemoryNamespace
    scope: MemoryScope
    owner_agent_id: str | None = None
    description: str = ""
    private: bool = False
    shared_read: bool = False


class MemoryWriteRequest(AIpinhoModel):
    agent_id: str
    namespace: MemoryNamespace
    scope: MemoryScope | None = None
    title: str
    content_sanitized: str
    memory_type: MemoryType = "summary"
    source_type: MemorySourceType = "agent_summary"
    source_ref: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: MemoryConfidence = "low"
    validation_status: MemoryValidationStatus | None = None
    tags: list[str] = Field(default_factory=list)
    project_id: str | None = None
    workspace_id: str | None = None
    supersedes: str | None = None
    reason: str = ""
    session_id: str | None = None
    run_id: str | None = None
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class MemoryCandidateCreateRequest(AIpinhoModel):
    proposed_by_agent_id: str
    namespace: MemoryNamespace
    scope: MemoryScope | None = None
    title: str
    content_sanitized: str
    memory_type: MemoryType = "summary"
    source_ref: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: MemoryConfidence = "low"
    reason_to_remember: str = ""
    session_id: str | None = None
    run_id: str | None = None
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class MemorySearchRequest(AIpinhoModel):
    agent_id: str
    query: str | None = None
    namespaces: list[MemoryNamespace] = Field(default_factory=list)
    memory_type: MemoryType | None = None
    tags: list[str] = Field(default_factory=list)
    project_id: str | None = None
    workspace_id: str | None = None
    include_candidates: bool = False
    include_stale: bool = True
    limit: int = 20
    session_id: str | None = None
    run_id: str | None = None
    reason: str = "memory_search"


class MemoryPolicyEvaluation(AIpinhoModel):
    decision: MemoryPolicyDecision
    reason_code: str
    human_reason: str
    warnings: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class MemoryWriteResult(AIpinhoModel):
    status: str
    memory: MemoryRecord | None = None
    candidate: MemoryCandidate | None = None
    policy: MemoryPolicyEvaluation
    warnings: list[str] = Field(default_factory=list)


class MemorySearchResult(AIpinhoModel):
    status: str
    records: list[MemoryRecord] = Field(default_factory=list)
    candidates: list[MemoryCandidate] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    access_logs: list[MemoryAccessLog] = Field(default_factory=list)


class MemoryContextLoadRequest(AIpinhoModel):
    agent_id: str
    session_id: str | None = None
    run_id: str | None = None
    workspace_id: str | None = None
    project_id: str | None = None
    limit: int = 20
    max_chars: int = 40000
    reason: str = "run_context_load"


class MemoryContextLoadResult(AIpinhoModel):
    status: str
    agent_id: str
    run_id: str | None = None
    memory_refs_used: list[str] = Field(default_factory=list)
    records: list[MemoryRecord] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    context_sanitized: str = ""


class MemoryCandidateReviewRequest(AIpinhoModel):
    agent_id: str
    reason: str = ""
    validation_status: MemoryValidationStatus = "validated"
    reviewed_by: str | None = None


class MemorySupersedeRequest(AIpinhoModel):
    agent_id: str
    replacement_memory_id: str | None = None
    reason: str
