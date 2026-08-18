from __future__ import annotations

from typing import Any

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class WorkspaceEvidenceBundleRequest(AIpinhoModel):
    session_id: str
    operation_id: str
    workspace_ref: str
    prompt: str
    summary_relative_path: str
    archive_relative_path: str
    source_relative_paths: list[str] = Field(default_factory=list)
    include_globs: list[str] = Field(default_factory=list)
    title: str = "Evidence Bundle Summary"
    execution_mode: str = "governed_autorun"


class WorkspaceEvidenceBundleResult(AIpinhoModel):
    status: str
    run_id: str | None = None
    summary_tool_invocation_id: str | None = None
    archive_tool_invocation_id: str | None = None
    summary_path: str | None = None
    archive_path: str | None = None
    artifact_id: str | None = None
    download_endpoint: str | None = None
    validation_status: str | None = None
    entries: list[str] = Field(default_factory=list)
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    reason_code: str | None = None
