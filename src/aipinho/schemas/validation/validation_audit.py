from __future__ import annotations
from pydantic import Field
from aipinho.schemas.common.base import AIpinhoModel

class ValidationAudit(AIpinhoModel):
    validation_id: str
    target_type: str
    target_id: str | None = None
    status: str
    reason: str = ""
    trace_ref: str | None = None
    warnings: list[str] = Field(default_factory=list)
