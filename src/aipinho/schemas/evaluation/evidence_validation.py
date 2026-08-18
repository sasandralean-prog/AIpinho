from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class EvidenceValidationResult(AIpinhoModel):
    valid: bool
    required: bool = False
    evidence_ids_seen: list[str] = Field(default_factory=list)
    missing_evidence_claims: list[str] = Field(default_factory=list)
    unseen_file_refs: list[str] = Field(default_factory=list)
    violations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
