from __future__ import annotations
from pydantic import Field
from aipinho.schemas.common.base import AIpinhoModel

class EvidenceCompliance(AIpinhoModel):
    status: str
    findings_checked: int = 0
    evidence_checked: int = 0
    missing_evidence: list[str] = Field(default_factory=list)
    invalid_evidence: list[str] = Field(default_factory=list)
