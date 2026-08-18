from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class PatchScope(AIpinhoModel):
    workspace: str
    affected_paths: list[str] = Field(default_factory=list)
    max_files: int = 5
    omitted_paths: list[str] = Field(default_factory=list)
