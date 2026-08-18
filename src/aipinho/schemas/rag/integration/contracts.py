from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

UsageMode = Literal[
    "explicit_user_request",
    "task_contract_allowed",
    "role_pipeline_allowed",
    "automatic_chat",
    "automatic_prompt_assembly",
]
PolicyStatus = Literal["allowed", "allowed_with_warnings", "blocked", "degraded"]
AdmissionStatus = Literal["admitted", "admitted_with_warnings", "partial", "blocked", "rejected", "degraded"]
PlanStatus = Literal["ready", "partial", "blocked", "degraded"]
ContextKind = Literal["retrieval_hit", "curated_memory", "evidence_item", "report_section", "file_excerpt", "visual_evidence", "ocr_text_block", "vision_context_item", "ocr_context_item"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ContextUsageTrace(AIpinhoModel):
    stage: str
    status: str
    reason: str
    data: dict[str, Any] = Field(default_factory=dict)


class ContextUsageAudit(AIpinhoModel):
    audit_id: str = Field(default_factory=lambda: f"context_audit_{uuid4().hex}")
    subject_id: str
    subject_type: str
    status: str
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)


class RAGMemoryPolicyRequest(AIpinhoModel):
    usage_mode: UsageMode
    intent_type: str = "conversation"
    task_type: str | None = None
    workspace: str | None = None
    requested_sources: list[str] = Field(default_factory=list)
    allow_curated_memory: bool = False
    allow_retrieval: bool = False
    scope: dict[str, Any] = Field(default_factory=dict)
    user_request: str = ""
    include_trace: bool = False


class RAGMemoryPolicyDecision(AIpinhoModel):
    decision_id: str = Field(default_factory=lambda: f"rag_memory_decision_{uuid4().hex}")
    allowed: bool = False
    status: PolicyStatus = "blocked"
    usage_mode: UsageMode
    allowed_sources: list[str] = Field(default_factory=list)
    blocked_sources: list[str] = Field(default_factory=list)
    allow_retrieval: bool = False
    allow_curated_memory: bool = False
    requires_context_admission: bool = True
    requires_citations: bool = True
    requires_budget: bool = True
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    trace: list[ContextUsageTrace] = Field(default_factory=list)


class ContextProvenance(AIpinhoModel):
    source_type: str
    source_id: str
    retrieval_id: str | None = None
    memory_id: str | None = None
    memory_version: int | None = None
    citation_id: str
    origin_reason: str
    content_hash: str | None = None
    source_ref: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now)


class ContextInjectionItem(AIpinhoModel):
    context_item_id: str = Field(default_factory=lambda: f"context_item_{uuid4().hex}")
    kind: ContextKind
    source_type: str
    source_id: str
    content: str
    citation_ids: list[str] = Field(default_factory=list)
    provenance: ContextProvenance
    score: float = 0.0
    rank: int = 1
    truncated: bool = False
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievalContextItem(ContextInjectionItem):
    kind: Literal["retrieval_hit", "evidence_item", "report_section", "file_excerpt"] = "retrieval_hit"


class MemoryContextItem(ContextInjectionItem):
    kind: Literal["curated_memory"] = "curated_memory"


class ContextConflict(AIpinhoModel):
    conflict_id: str = Field(default_factory=lambda: f"context_conflict_{uuid4().hex}")
    severity: Literal["low", "medium", "high"] = "medium"
    item_ids: list[str] = Field(default_factory=list)
    pattern: str
    reason: str
    resolved: bool = False


class ContextFreshness(AIpinhoModel):
    status: Literal["fresh", "stale_warning", "blocked", "unknown"] = "unknown"
    item_statuses: dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)


class ContextBudgetResult(AIpinhoModel):
    status: Literal["fit", "partial", "blocked"] = "fit"
    max_items: int = 12
    max_chars: int = 24000
    input_items: int = 0
    admitted_items: int = 0
    retrieval_items: int = 0
    memory_items: int = 0
    used_chars: int = 0
    omitted_item_ids: list[str] = Field(default_factory=list)
    truncated_item_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ContextCitationMap(AIpinhoModel):
    item_to_citations: dict[str, list[str]] = Field(default_factory=dict)
    citations: dict[str, dict[str, Any]] = Field(default_factory=dict)
    valid: bool = False
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)


class ContextAdmissionRequest(AIpinhoModel):
    policy_decision: RAGMemoryPolicyDecision
    retrieval_result: dict[str, Any] | None = None
    retrieval_context_bundle: dict[str, Any] | None = None
    memory_items: list[dict[str, Any]] = Field(default_factory=list)
    attachment_context_items: list[dict[str, Any]] = Field(default_factory=list)
    scope: dict[str, Any] = Field(default_factory=dict)
    budget: dict[str, Any] = Field(default_factory=dict)
    usage_mode: UsageMode = "explicit_user_request"
    include_trace: bool = False


class ContextAdmissionDecision(AIpinhoModel):
    admission_id: str = Field(default_factory=lambda: f"context_admission_{uuid4().hex}")
    status: AdmissionStatus = "blocked"
    usage_mode: UsageMode = "explicit_user_request"
    workspace: str | None = None
    admitted_items: list[ContextInjectionItem] = Field(default_factory=list)
    blocked_items: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    budget_result: ContextBudgetResult = Field(default_factory=ContextBudgetResult)
    conflicts: list[ContextConflict] = Field(default_factory=list)
    freshness: ContextFreshness = Field(default_factory=ContextFreshness)
    citation_map: ContextCitationMap = Field(default_factory=ContextCitationMap)
    safe_for_prompt_assembly: bool = False
    trace: list[ContextUsageTrace] = Field(default_factory=list)


class ContextInjectionPlan(AIpinhoModel):
    plan_id: str = Field(default_factory=lambda: f"context_plan_{uuid4().hex}")
    admission_id: str | None = None
    policy_decision_id: str | None = None
    status: PlanStatus = "blocked"
    usage_mode: UsageMode = "explicit_user_request"
    workspace: str | None = None
    context_items: list[ContextInjectionItem] = Field(default_factory=list)
    citation_map: ContextCitationMap = Field(default_factory=ContextCitationMap)
    source_summary: list[dict[str, Any]] = Field(default_factory=list)
    budget_summary: ContextBudgetResult = Field(default_factory=ContextBudgetResult)
    limitations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    safe_for_prompt_assembly: bool = False
    created_at: str = Field(default_factory=utc_now)
    trace: list[ContextUsageTrace] = Field(default_factory=list)


class RetrievalContextSelection(AIpinhoModel):
    items: list[ContextInjectionItem] = Field(default_factory=list)
    blocked_items: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)


class MemoryContextSelection(RetrievalContextSelection):
    pass


class ContextUsageValidation(AIpinhoModel):
    valid: bool
    status: Literal["accepted", "accepted_with_warnings", "rejected", "degraded"]
    used_citation_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    violations: list[str] = Field(default_factory=list)


class RAGMemoryStatus(AIpinhoModel):
    status: str
    integration_enabled: bool = True
    mode: str = "governed_policy_integration"
    auto_chat_retrieval_enabled: bool = False
    auto_prompt_injection_enabled: bool = False
    curated_memory_explicit_required: bool = True
    vectorstore_enabled: bool = False
    embeddings_enabled: bool = False
    auto_ingest_enabled: bool = False
    legacy_vectorstore_enabled: bool = False
    workspace_write_enabled: bool = False
    patch_enabled: bool = False
    shell_enabled: bool = False
    git_enabled: bool = False
    configs: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


