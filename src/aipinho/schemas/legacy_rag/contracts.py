
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ReviewStatus = Literal["approved", "rejected", "needs_human_review"]


class LegacySourceFile(BaseModel):
    source_id: str
    path: str
    relative_path: str
    source_root: str
    source_kind: str
    extension: str
    size_bytes: int
    sha256: str | None = None
    included: bool = True
    ignored_reason: str | None = None


class LegacySanitizedChunk(BaseModel):
    chunk_id: str
    source_id: str
    source_path: str
    source_hash: str
    chunk_index: int
    text: str
    summary: str
    source_kind: str
    citations: list[str] = Field(default_factory=list)
    redactions: list[str] = Field(default_factory=list)
    raw_reference: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class LegacyClassifiedChunk(LegacySanitizedChunk):
    categories: list[str] = Field(default_factory=list)
    scope: str = "historical_diagnostic"
    trust_level: str = "legacy_reference"
    current_truth_allowed: bool = False
    pinhoforge_specific: bool = False
    deprecated_signals: list[str] = Field(default_factory=list)


class LegacyConflict(BaseModel):
    conflict_id: str
    chunk_id: str
    conflict_type: str
    severity: str
    evidence: list[str] = Field(default_factory=list)
    resolution: str = "current_aipinho_wins"


class LegacyReviewDecision(BaseModel):
    chunk_id: str
    status: ReviewStatus
    reason: str
    allowed_uses: list[str] = Field(default_factory=list)
    blocked_uses: list[str] = Field(default_factory=list)
    reviewer: str = "policy_preview"


class LegacyImportStageResult(BaseModel):
    status: str
    stage: str
    counts: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    artifacts: dict[str, str] = Field(default_factory=dict)


class LegacyRAGStatus(BaseModel):
    status: str
    namespace_id: str
    namespace_committed: bool
    counts: dict[str, int] = Field(default_factory=dict)
    artifacts: dict[str, str] = Field(default_factory=dict)
