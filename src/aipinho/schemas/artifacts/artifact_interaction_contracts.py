from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


class ArtifactUploadRequest(AIpinhoModel):
    filename: str
    content: str
    encoding: str = "text"
    content_type: str = "text/plain"
    message_id: str | None = None
    source_agent: str | None = None
    owner_task_id: str | None = None
    bridge_task_id: str | None = None
    session_id: str | None = None
    validation_status: str = "validated"
    status: str = "ready"
    provenance: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArtifactRecord(AIpinhoModel):
    artifact_id: str = Field(default_factory=lambda: f"artifact_{uuid4().hex}")
    logical_path: str | None = None
    storage_ref: str | None = None
    artifact_type: str = "runtime_output"
    producer_step: str | None = None
    event_id: str | None = None
    task_id: str | None = None
    task_run_id: str | None = None
    source_agent: str | None = None
    owner_task_id: str | None = None
    bridge_task_id: str | None = None
    session_id: str | None = None
    filename: str
    content_type: str
    size_bytes: int
    sha256: str
    local_path: str | None = None
    storage_path: str
    download_endpoint: str | None = None
    requires_token: bool = True
    status: str = "ready"
    validation_status: str = "validated"
    evidence_refs: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    error_reason: str | None = None
    message_id: str | None = None
    direct_workspace_file: bool = False
    created_at: str = Field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArtifactUploadResponse(AIpinhoModel):
    artifact: ArtifactRecord
    download_path: str


class ArtifactDownloadLink(AIpinhoModel):
    artifact_id: str
    download_path: str
    requires_token: bool = True
    direct_workspace_file: bool = False


class UniversalArtifactCreateRequest(AIpinhoModel):
    source_agent: str
    filename: str
    logical_path: str | None = None
    artifact_type: str = "runtime_output"
    producer_step: str | None = None
    event_id: str | None = None
    task_id: str | None = None
    task_run_id: str | None = None
    content_type: str = "text/plain"
    content: str | None = None
    encoding: str = "text"
    local_path: str | None = None
    owner_task_id: str | None = None
    bridge_task_id: str | None = None
    session_id: str | None = None
    validation_status: str = "validated"
    status: str = "ready"
    allow_empty: bool = False
    evidence_refs: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    visible_to_agent_ids: list[str] = Field(default_factory=list)


class UniversalArtifactResponse(AIpinhoModel):
    status: str
    artifact: dict[str, Any]
    download_endpoint: str | None = None
    requires_token: bool = True


class ArtifactZipRequest(AIpinhoModel):
    artifact_ids: list[str]
    filename: str = "artifacts.zip"


class ArtifactZipResponse(AIpinhoModel):
    artifact: ArtifactRecord
    included_artifacts: list[str]
    download_path: str


class ArtifactPathArchiveRequest(AIpinhoModel):
    source_paths: list[str]
    filename: str = "paths.zip"
    operation_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArtifactPathArchiveSkippedPath(AIpinhoModel):
    path: str
    reason: str


class ArtifactPathArchiveResponse(AIpinhoModel):
    artifact: ArtifactRecord
    download_path: str
    included_paths: list[str] = Field(default_factory=list)
    skipped_paths: list[ArtifactPathArchiveSkippedPath] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class TaskRunArtifactExportRequest(AIpinhoModel):
    summary_filename: str | None = None
    zip_filename: str | None = None


class TaskRunArtifactExportResponse(AIpinhoModel):
    run_id: str
    summary_artifact: ArtifactRecord
    zip_artifact: ArtifactRecord
    summary_download_path: str
    zip_download_path: str
