from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


ArtifactType = Literal[
    "markdown_report",
    "text_export",
    "json_export",
    "zip_evidence",
    "patch_diff",
    "build_log",
    "test_log",
    "apk",
    "jar",
    "generic_file",
]

ArtifactGenerationStatus = Literal["READY", "READY_WITH_WARNINGS", "BLOCKED", "FAILED"]


class ArtifactRequest(AIpinhoModel):
    artifact_request_id: str = Field(default_factory=lambda: f"artifact_request_{uuid4().hex}")
    source_agent: str
    source_chat_id: str | None = None
    owner_task_id: str | None = None
    bridge_task_id: str | None = None
    artifact_type: ArtifactType = "markdown_report"
    requested_filename: str
    content_source: str = "inline"
    content_inline: str | None = None
    source_paths: list[str] = Field(default_factory=list)
    include_patterns: list[str] = Field(default_factory=list)
    exclude_patterns: list[str] = Field(default_factory=list)
    workspace: str | None = None
    requires_validation: bool = True
    user_visible: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now_iso)


class ArtifactGenerationResult(AIpinhoModel):
    artifact_request_id: str
    artifact_id: str | None = None
    status: ArtifactGenerationStatus
    source_agent: str
    executor_agent: str
    filename: str | None = None
    local_path: str | None = None
    content_type: str | None = None
    size_bytes: int = 0
    validation_status: str = "unknown"
    validation_errors: list[str] = Field(default_factory=list)
    artifact_refs: list[dict[str, Any]] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now_iso)
    download_endpoint: str | None = None
    requires_token: bool = True

