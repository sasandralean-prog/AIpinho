from __future__ import annotations
from pydantic import Field
from aipinho.schemas.common.base import AIpinhoModel

class ReportQualityRule(AIpinhoModel):
    rule_id: str
    enabled: bool = True
    severity: str = "warning"
    description: str = ""
    required_fields: list[str] = Field(default_factory=list)
