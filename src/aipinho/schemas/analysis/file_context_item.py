from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from aipinho.schemas.analysis.analysis_trace import AnalysisTraceItem
from aipinho.schemas.common.base import AIpinhoModel

FileContextStatus = Literal["included", "omitted", "blocked", "invalid"]


class FileContextItem(AIpinhoModel):
    path: str
    status: FileContextStatus
    content: str | None = None
    content_truncated: bool = False
    size_bytes: int | None = None
    bytes_read: int | None = None
    extension: str | None = None
    execution_id: str | None = None
    warnings: list[str] = Field(default_factory=list)
    violations: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    trace: list[AnalysisTraceItem] = Field(default_factory=list)
