from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class ProjectRebuildFileEntry(AIpinhoModel):
    relative_path: str
    source_path: str
    target_path: str
    size_bytes: int = 0
    line_count: int = 0
    status: str = "included"
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)


class ProjectRebuildPreviewRequest(AIpinhoModel):
    session_id: str | None = None
    prompt: str = ""
    source_workspace: str | None = None
    target_workspace: str
    source_run_id: str | None = None
    operation_id: str | None = None
    include_trace: bool = False


class ProjectRebuildPreviewResult(AIpinhoModel):
    status: str
    operation_id: str
    source_workspace: str | None = None
    target_workspace: str
    source_run_id: str | None = None
    plan_id: str | None = None
    quality_id: str | None = None
    approval_id: str | None = None
    files: list[ProjectRebuildFileEntry] = Field(default_factory=list)
    omitted_files: list[ProjectRebuildFileEntry] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    message: str = ""
    trace: list[dict[str, object]] = Field(default_factory=list)
