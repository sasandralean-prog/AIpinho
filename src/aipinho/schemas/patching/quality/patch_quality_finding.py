from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class PatchQualityFinding(AIpinhoModel):
    finding_id: str
    category: str
    severity: str = "info"
    message: str
    file_path: str | None = None
    line: int | None = None
    blocking: bool = False
    evidence_id: str | None = None
    recommendation: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)
