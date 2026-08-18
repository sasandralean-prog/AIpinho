from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.reports.evidence_citation import EvidenceCitation
from aipinho.schemas.reports.report_trace import ReportTraceItem

FindingCategory = Literal["architecture", "policy", "routing", "schema", "service", "test", "security", "maintainability", "documentation", "risk", "limitations"]
FindingSeverity = Literal["info", "low", "medium", "high", "critical"]


class EvidenceFinding(AIpinhoModel):
    finding_id: str
    title: str
    category: FindingCategory
    severity: FindingSeverity
    confidence: float = 0.0
    summary: str
    evidence: list[EvidenceCitation] = Field(default_factory=list)
    inference: str = ""
    recommendation: str = ""
    requires_write: bool = False
    requires_followup: bool = False
    trace: list[ReportTraceItem] = Field(default_factory=list)
