from __future__ import annotations

from typing import Any

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class ProjectAnalysisRequest(AIpinhoModel):
    workspace: str
    prompt: str = ""
    goal: str = "general_project_analysis"
    workspace_context: dict[str, Any] = Field(default_factory=dict)
    focus_paths: list[str] = Field(default_factory=list)
    max_files: int | None = None
    max_total_bytes: int | None = None
    max_file_bytes: int | None = None
    max_single_file_read_ms: int | None = None
    include_trace: bool = False
