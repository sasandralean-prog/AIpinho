from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class ModelDoctorCheck(AIpinhoModel):
    name: str
    status: str
    summary: str
    blocked_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    evidence: dict[str, object] = Field(default_factory=dict)
