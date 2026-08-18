from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.memory.memory_candidate import MemoryCandidateEvidence, MemoryCandidateRisk, MemoryCandidateScope, MemoryCandidateSource

CuratedMemoryStatus = Literal["active", "superseded", "expired", "rejected"]


class CuratedMemorySource(MemoryCandidateSource):
    candidate_id: str
    approval_id: str


class CuratedMemoryEvidence(MemoryCandidateEvidence):
    pass


class CuratedMemoryScope(MemoryCandidateScope):
    pass


class CuratedMemoryVersion(AIpinhoModel):
    memory_id: str
    version: int
    status: CuratedMemoryStatus
    created_at: str
    candidate_id: str
    approval_id: str
    summary_hash: str
    supersedes: str | None = None
    reason: str = ""


class CuratedMemoryTrace(AIpinhoModel):
    stage: str
    status: str
    reason: str
    data: dict[str, Any] = Field(default_factory=dict)


class CuratedMemoryEvent(AIpinhoModel):
    event_id: str
    memory_id: str
    event_type: str
    status: str
    message: str
    created_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class CuratedMemoryAudit(AIpinhoModel):
    memory_id: str
    event_type: str
    created_at: str
    candidate_id: str | None = None
    approval_id: str | None = None
    vectorstore_written: bool = False
    embeddings_generated: bool = False
    rag_enabled: bool = False


class CuratedMemory(AIpinhoModel):
    memory_id: str
    status: CuratedMemoryStatus = "active"
    kind: str
    summary: str
    text: str
    source: CuratedMemorySource
    scope: CuratedMemoryScope
    evidence: list[CuratedMemoryEvidence] = Field(default_factory=list)
    confidence: str = "medium"
    risk: MemoryCandidateRisk = Field(default_factory=MemoryCandidateRisk)
    version: int = 1
    supersedes: str | None = None
    superseded_by: str | None = None
    tags: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    trace: list[CuratedMemoryTrace] = Field(default_factory=list)
    created_at: str
    updated_at: str


class CuratedMemoryRequest(AIpinhoModel):
    candidate_id: str
    approval_id: str
    operator_confirmed: bool = False
    resolution: str | None = None
    supersede_memory_id: str | None = None
    reason: str = ""


class CuratedMemoryResult(AIpinhoModel):
    status: str
    memory: CuratedMemory | None = None
    blocked_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    vectorstore_enabled: bool = False
    embeddings_enabled: bool = False
    rag_enabled: bool = False
    auto_prompt_memory_enabled: bool = False


class MemoryApprovalRequest(AIpinhoModel):
    candidate_id: str
    reason: str = ""
    operator_confirmed: bool = False


class MemoryApprovalResult(AIpinhoModel):
    status: str
    approval_id: str | None = None
    candidate_id: str
    persisted: bool = False
    approved_memory_enabled: bool = True
    approval_required: bool = True
    persist_requires_explicit_endpoint: bool = True
    blocked_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class MemoryPersistenceValidation(AIpinhoModel):
    allowed: bool
    status: str
    blocked_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    trace: list[CuratedMemoryTrace] = Field(default_factory=list)


class MemorySupersedeRequest(AIpinhoModel):
    candidate_id: str
    approval_id: str
    reason: str
    operator_confirmed: bool = False


class MemoryExpirationRequest(AIpinhoModel):
    reason: str


class MemorySearchRequest(AIpinhoModel):
    status: str | None = None
    kind: str | None = None
    scope: str | None = None
    workspace: str | None = None
    source_type: str | None = None
    confidence: str | None = None
    risk: str | None = None
    text: str | None = None
    tag: str | None = None
    limit: int = 100


class MemorySearchResult(AIpinhoModel):
    status: str
    results: list[CuratedMemory] = Field(default_factory=list)
    search_mode: str = "deterministic"
    vectorstore_enabled: bool = False
    embeddings_enabled: bool = False
    rag_enabled: bool = False
