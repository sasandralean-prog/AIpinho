from __future__ import annotations

from typing import Any

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class WorkspaceReadonlyAuditReportRequest(AIpinhoModel):
    session_id: str
    operation_id: str
    workspace_ref: str
    prompt: str
    report_relative_path: str
    search_terms: list[str] = Field(default_factory=list)
    execution_mode: str = "governed_autorun"
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkspaceReadonlyAuditReportResult(AIpinhoModel):
    status: str
    reason_code: str | None = None
    run_id: str | None = None
    report_tool_invocation_id: str | None = None
    report_path: str | None = None
    validation_status: str | None = None
    matched_files: list[str] = Field(default_factory=list)
    match_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    evidence_refs: list[dict[str, str]] = Field(default_factory=list)
