from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class PatchQualityGateRequest(AIpinhoModel):
    plan_id: str | None = None
    workspace: str | None = None
    diff_text: str = ""
    file_contents: dict[str, str] = Field(default_factory=dict)
    target_files: list[str] = Field(default_factory=list)
    test_recommendations: list[str] = Field(default_factory=list)
    rollback_notes: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)
