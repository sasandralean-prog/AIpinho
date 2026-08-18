from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

WorkspaceIndexStatus = Literal[
    "draft",
    "previewed",
    "pending_approval",
    "indexing",
    "indexed",
    "partial",
    "failed",
    "blocked",
    "expired",
]


class WorkspaceIndexRequest(AIpinhoModel):
    index_request_id: str
    workspace_id: str
    workspace_path: str
    source_channel: str = "api"
    session_id: str | None = None
    requested_by: str = "user"
    scope: str = "workspace"
    include_patterns: list[str] = Field(default_factory=lambda: ["**/*"])
    exclude_patterns: list[str] = Field(default_factory=list)
    respect_gitignore: bool = True
    max_file_size: int = 512000
    max_total_size: int = 5000000
    secret_scan_enabled: bool = True
    embeddings_required: bool = False
    reranker_required: bool = False
    ocr_enabled: bool = False
    vision_enabled: bool = False
    external_provider_allowed: bool = False
    policy_decision: dict[str, object] = Field(default_factory=dict)
    approval_id: str | None = None
    status: WorkspaceIndexStatus = "draft"


class WorkspaceIndexRecord(AIpinhoModel):
    request: WorkspaceIndexRequest
    indexed_files: list[dict[str, object]] = Field(default_factory=list)
    skipped_files: list[dict[str, object]] = Field(default_factory=list)
    capabilities_used: dict[str, object] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    route_decision: dict[str, object] = Field(default_factory=dict)
    created_at: str
    updated_at: str
