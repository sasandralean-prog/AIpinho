from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


RetrievalStatus = Literal["found", "partial", "no_results", "blocked", "degraded", "invalid"]
RetrievalSourceType = Literal["file", "project_report", "task_run_result", "validation_result", "patch_apply_result", "curated_memory"]
CitationType = Literal["file_line_range", "report_section", "evidence_id", "task_result_field", "validation_finding", "patch_apply_field", "memory_id"]


class RetrievalTrace(AIpinhoModel):
    stage: str
    status: str
    reason: str
    source_id: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class RetrievalAudit(AIpinhoModel):
    retrieval_id: str
    status: str
    sources: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    trace_ref: str | None = None


class RetrievalBudget(AIpinhoModel):
    max_sources_per_request: int = 5
    max_hits_total: int = 20
    max_hits_per_source: int = 8
    max_files_read: int = 20
    max_file_bytes: int = 200000
    max_total_bytes: int = 500000
    max_context_chars: int = 30000
    max_hit_excerpt_chars: int = 1200
    max_citation_excerpt_chars: int = 500
    max_query_chars: int = 1000
    truncate_large_hits: bool = True


class RetrievalScope(AIpinhoModel):
    scope_type: str = "project"
    workspace: str | None = None
    project: str | None = None
    source_ids: list[str] = Field(default_factory=list)
    reason: str = "explicit_retrieval_request"


class RetrievalQuery(AIpinhoModel):
    text: str
    normalized: str = ""
    tokens: list[str] = Field(default_factory=list)


class SourceRef(AIpinhoModel):
    source_id: str
    source_type: str
    ref: str
    location: str | None = None
    content_hash: str | None = None


class Citation(AIpinhoModel):
    citation_id: str = Field(default_factory=lambda: f"citation_{uuid4().hex}")
    citation_type: CitationType
    source_ref: SourceRef
    excerpt: str
    line_start: int | None = None
    line_end: int | None = None
    section: str | None = None
    evidence_id: str | None = None
    confidence: float = 1.0


class EvidenceBundle(AIpinhoModel):
    evidence_bundle_id: str = Field(default_factory=lambda: f"evidence_bundle_{uuid4().hex}")
    status: str = "valid"
    citations: list[Citation] = Field(default_factory=list)
    evidence_count: int = 0
    valid: bool = True
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)


class RetrievalSource(AIpinhoModel):
    source_id: str
    source_type: str
    adapter: str
    enabled: bool = True
    read_only: bool = True
    requires_workspace: bool = False
    explicit_request_required: bool = False
    auto_enabled_in_chat: bool = False
    auto_enabled_in_prompt: bool = False
    description: str = ""
    reason: str | None = None


class RetrievalSourcePolicy(AIpinhoModel):
    source_id: str
    allowed: bool
    status: str
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class RetrievalHit(AIpinhoModel):
    hit_id: str = Field(default_factory=lambda: f"hit_{uuid4().hex}")
    source_id: str
    source_type: str
    title: str = ""
    excerpt: str
    score: float = 0.0
    citation: Citation | None = None
    source_ref: SourceRef | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    blocked: bool = False
    blocked_reason: str | None = None


class RetrievalValidation(AIpinhoModel):
    valid: bool
    status: str
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)


class RetrievalContextBundle(AIpinhoModel):
    bundle_id: str = Field(default_factory=lambda: f"retrieval_bundle_{uuid4().hex}")
    retrieval_id: str | None = None
    status: RetrievalStatus = "no_results"
    query: str = ""
    hits: list[RetrievalHit] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    evidence_bundle: EvidenceBundle = Field(default_factory=EvidenceBundle)
    budget: RetrievalBudget = Field(default_factory=RetrievalBudget)
    source_refs: list[SourceRef] = Field(default_factory=list)
    scope: RetrievalScope = Field(default_factory=RetrievalScope)
    safe_for_prompt_assembly: bool = False
    context_text: str = ""
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)


class RetrievalRequest(AIpinhoModel):
    retrieval_request_id: str = Field(default_factory=lambda: f"retrieval_request_{uuid4().hex}")
    query: str
    sources: list[str] = Field(default_factory=list)
    scope: RetrievalScope = Field(default_factory=RetrievalScope)
    budget: RetrievalBudget = Field(default_factory=RetrievalBudget)
    workspace: str | None = None
    paths: list[str] = Field(default_factory=list)
    report_id: str | None = None
    run_id: str | None = None
    validation_id: str | None = None
    apply_run_id: str | None = None
    memory_id: str | None = None
    explicit: bool = False
    include_trace: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievalResult(AIpinhoModel):
    retrieval_id: str = Field(default_factory=lambda: f"retrieval_{uuid4().hex}")
    status: RetrievalStatus
    query: RetrievalQuery
    sources_requested: list[str] = Field(default_factory=list)
    sources_used: list[str] = Field(default_factory=list)
    hits: list[RetrievalHit] = Field(default_factory=list)
    context_bundle: RetrievalContextBundle | None = None
    evidence_bundle: EvidenceBundle | None = None
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    trace: list[RetrievalTrace] = Field(default_factory=list)
    audit: RetrievalAudit | None = None
    vectorstore_used: bool = False
    embeddings_used: bool = False
    legacy_vectorstore_used: bool = False
    side_effects: bool = False
