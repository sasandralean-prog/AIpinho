from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

ContextPurpose = str
ContextLayer = str
ContextSourceType = str
ContextTrustLevel = str
ContextFreshnessStatus = str
AdmissionStatus = str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class ContextScope(AIpinhoModel):
    session_id: str | None = None
    task_id: str | None = None
    workspace_id: str | None = None
    role_id: str | None = None
    intent_id: str | None = None
    trace_id: str | None = None


class ContextSourceRef(AIpinhoModel):
    source_type: ContextSourceType
    source_id: str
    path: str | None = None
    uri: str | None = None
    citation_id: str | None = None
    source_hash: str | None = None


class ContextCitation(AIpinhoModel):
    citation_id: str = Field(default_factory=lambda: f"citation_{uuid4().hex}")
    source_ref: ContextSourceRef
    label: str | None = None
    page: int | None = None
    region: str | None = None
    confidence: float | None = None


class ContextEvidenceRef(AIpinhoModel):
    evidence_id: str = Field(default_factory=lambda: f"evidence_{uuid4().hex}")
    source_ref: ContextSourceRef
    summary: str
    confidence: float | None = None


class ChunkFreshness(AIpinhoModel):
    status: ContextFreshnessStatus = "fresh"
    checked_at: str = Field(default_factory=utc_now_iso)
    expires_at: str | None = None
    reason: str | None = None


class ContextWarning(AIpinhoModel):
    code: str
    message: str


class ContextBudget(AIpinhoModel):
    max_chars: int = 8000
    used_chars: int = 0
    remaining_chars: int = 8000


class ContextBudgetResult(AIpinhoModel):
    status: str
    requested_chars: int
    admitted_chars: int
    truncated_chars: int = 0
    max_chars: int


class ContextBudgetPolicyResult(AIpinhoModel):
    purpose: ContextPurpose
    max_chars: int
    layer_budgets: dict[str, int] = Field(default_factory=dict)


class ContextCandidate(AIpinhoModel):
    candidate_id: str = Field(default_factory=lambda: f"candidate_{uuid4().hex}")
    layer: ContextLayer
    source_type: ContextSourceType
    source_ref: ContextSourceRef | None = None
    summary: str
    content: str = ""
    priority: int = 5
    trust_level: ContextTrustLevel = "candidate"
    freshness: ChunkFreshness = Field(default_factory=ChunkFreshness)
    citations: list[ContextCitation] = Field(default_factory=list)
    evidence_refs: list[ContextEvidenceRef] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ContextAdmissionDecision(AIpinhoModel):
    decision_id: str = Field(default_factory=lambda: f"decision_{uuid4().hex}")
    candidate_id: str
    status: AdmissionStatus
    reason_codes: list[str] = Field(default_factory=list)
    human_reason: str = ""
    policy_refs: list[str] = Field(default_factory=list)
    budget_result: ContextBudgetResult | None = None
    warnings: list[ContextWarning] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)


class ContextRejectionReason(AIpinhoModel):
    candidate_id: str
    code: str
    human_reason: str


class ContextItem(AIpinhoModel):
    item_id: str = Field(default_factory=lambda: f"context_item_{uuid4().hex}")
    layer: ContextLayer
    source_type: ContextSourceType
    source_ref: ContextSourceRef
    summary: str
    content: str
    content_hash: str
    citations: list[ContextCitation] = Field(default_factory=list)
    evidence_refs: list[ContextEvidenceRef] = Field(default_factory=list)
    trust_level: ContextTrustLevel = "candidate"
    freshness: ChunkFreshness = Field(default_factory=ChunkFreshness)
    budget_chars: int = 0
    injection_slot: str | None = None
    warnings: list[ContextWarning] = Field(default_factory=list)


class CitationMap(AIpinhoModel):
    citations: dict[str, ContextCitation] = Field(default_factory=dict)


class ContextBundleMetadata(AIpinhoModel):
    created_by: str = "context_kernel"
    cache_used: bool = False
    policy_version: str = "1"


class ContextBundleSummary(AIpinhoModel):
    item_count: int
    rejected_count: int
    warning_count: int
    total_chars: int


class ContextBundle(AIpinhoModel):
    bundle_id: str = Field(default_factory=lambda: f"bundle_{uuid4().hex}")
    request_id: str
    purpose: ContextPurpose
    scope: ContextScope
    items: list[ContextItem] = Field(default_factory=list)
    citation_map: dict[str, ContextCitation] = Field(default_factory=dict)
    budget: ContextBudget = Field(default_factory=ContextBudget)
    admission_decisions: list[ContextAdmissionDecision] = Field(default_factory=list)
    rejected_items: list[ContextRejectionReason] = Field(default_factory=list)
    warnings: list[ContextWarning] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    safe_for_prompt: bool = True
    metadata: ContextBundleMetadata = Field(default_factory=ContextBundleMetadata)
    created_at: str = Field(default_factory=utc_now_iso)
    trace_id: str | None = None


class ContextTrace(AIpinhoModel):
    trace_id: str = Field(default_factory=lambda: f"context_trace_{uuid4().hex}")
    request_id: str
    bundle_id: str | None = None
    steps: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)


class ContextAudit(AIpinhoModel):
    audit_id: str = Field(default_factory=lambda: f"context_audit_{uuid4().hex}")
    action: str
    request_id: str | None = None
    bundle_id: str | None = None
    created_at: str = Field(default_factory=utc_now_iso)
    details: dict[str, Any] = Field(default_factory=dict)


class SmartChunk(AIpinhoModel):
    chunk_id: str = Field(default_factory=lambda: f"chunk_{uuid4().hex}")
    text: str
    chunk_type: str = "unknown"
    source_ref: ContextSourceRef | None = None
    content_hash: str | None = None
    trust_level: ContextTrustLevel = "candidate"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChunkClassification(AIpinhoModel):
    chunk_id: str
    chunk_type: str
    trust_level: ContextTrustLevel
    confidence: float = 0.5


class ChunkSourceMetadata(AIpinhoModel):
    source_ref: ContextSourceRef
    title: str | None = None
    created_at: str | None = None


class ContextCacheKey(AIpinhoModel):
    key: str
    purpose: ContextPurpose
    scope_hash: str
    candidates_hash: str
    policy_version: str = "1"


class ContextCacheEntry(AIpinhoModel):
    key: str
    bundle_id: str
    source_hashes: dict[str, str] = Field(default_factory=dict)
    policy_version: str = "1"
    created_at: str = Field(default_factory=utc_now_iso)


class ContextCacheStatus(AIpinhoModel):
    status: str
    enabled: bool
    entries: int


class ContextCacheInvalidation(AIpinhoModel):
    reason: str
    scope: ContextScope | None = None
    source_ref: ContextSourceRef | None = None
    policy_version: str | None = None


class ContextPromptSlot(AIpinhoModel):
    slot_id: str
    items: list[str] = Field(default_factory=list)
    max_chars: int = 0


class ContextCompressionResult(AIpinhoModel):
    status: str
    original_chars: int
    compressed_chars: int
    citations_preserved: bool = True


class ContextInjectionPlan(AIpinhoModel):
    plan_id: str = Field(default_factory=lambda: f"context_plan_{uuid4().hex}")
    bundle_id: str
    role_id: str | None = None
    purpose: ContextPurpose
    safe_for_prompt_assembly: bool = True
    slots: list[ContextPromptSlot] = Field(default_factory=list)
    citation_map: dict[str, ContextCitation] = Field(default_factory=dict)
    blocked_items: list[str] = Field(default_factory=list)
    warnings: list[ContextWarning] = Field(default_factory=list)


class ContextRequest(AIpinhoModel):
    request_id: str = Field(default_factory=lambda: f"context_request_{uuid4().hex}")
    purpose: ContextPurpose
    scope: ContextScope = Field(default_factory=ContextScope)
    current_message: str | None = None
    candidates: list[ContextCandidate] = Field(default_factory=list)
    role_id: str | None = None
    max_budget_chars: int | None = None
    persist: bool = False
    requested_by: str = "backend"


class ContextPreviewRequest(ContextRequest):
    persist: bool = False


class ContextBuildRequest(ContextRequest):
    persist: bool = True


class ContextPreviewResult(AIpinhoModel):
    status: str
    bundle: ContextBundle
    cache_used: bool = False


class ContextBuildResult(AIpinhoModel):
    status: str
    bundle: ContextBundle


class ContextExplainResult(AIpinhoModel):
    bundle_id: str
    item_explanations: list[dict[str, Any]] = Field(default_factory=list)
    rejection_explanations: list[ContextRejectionReason] = Field(default_factory=list)


class ContextStatus(AIpinhoModel):
    status: str
    enabled: bool
    context_admission_owner: str
    context_bundle_builder_enabled: bool
    context_cache_enabled: bool
    smart_chunks_enabled: bool
    safe_for_prompt_required: bool
    raw_context_blocked: bool
    citations_required_for_contextual_claims: bool
