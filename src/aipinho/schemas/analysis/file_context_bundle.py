from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.analysis.analysis_trace import AnalysisTraceItem
from aipinho.schemas.analysis.file_context_item import FileContextItem
from aipinho.schemas.analysis.file_selection import FileSelectionCandidate
from aipinho.schemas.common.base import AIpinhoModel

FileContextBundleStatus = Literal["ok", "partial", "blocked", "invalid", "degraded"]


class FileContextBundle(AIpinhoModel):
    bundle_id: str
    workspace: str
    status: FileContextBundleStatus
    items: list[FileContextItem] = Field(default_factory=list)
    omitted_files: list[FileSelectionCandidate] = Field(default_factory=list)
    total_bytes_read: int = 0
    max_total_bytes: int | None = None
    warnings: list[str] = Field(default_factory=list)
    violations: list[str] = Field(default_factory=list)
    trace: list[AnalysisTraceItem] = Field(default_factory=list)
    read_plan: dict[str, object] | None = None
