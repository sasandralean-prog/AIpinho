from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.reports.evidence import EvidenceSourceType


class EvidenceCitation(AIpinhoModel):
    evidence_id: str
    source_type: EvidenceSourceType
    path: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    excerpt: str | None = None
    hash: str | None = None
    confidence: float = 0.0
    read_audit_event_id: str | None = None
    notes: list[str] = Field(default_factory=list)
