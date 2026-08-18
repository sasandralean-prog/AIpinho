from __future__ import annotations
from aipinho.schemas.common.base import AIpinhoModel

class ReportQualityScore(AIpinhoModel):
    score: float
    status: str
    findings_count: int = 0
    evidence_count: int = 0
