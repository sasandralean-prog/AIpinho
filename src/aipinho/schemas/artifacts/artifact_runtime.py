from __future__ import annotations

from typing import Any

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.artifacts.artifact_semantic_profile import ArtifactSemanticProfile


class ArtifactRuntimeCreateRequest(AIpinhoModel):
    logical_path: str
    content: str
    encoding: str = "text"
    artifact_type: str = "runtime_output"
    content_type: str = "text/plain"
    producer_step: str
    event_id: str | None = None
    task_id: str | None = None
    task_run_id: str | None = None
    source_agent: str = "aipinho_runtime"
    session_id: str | None = None
    validation_status: str = "pending"
    status: str = "ready"
    evidence_refs: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArtifactRuntimeValidationResult(AIpinhoModel):
    artifact_id: str
    status: str
    validation_status: str
    logical_path: str | None = None
    storage_ref: str | None = None
    size_bytes: int = 0
    sha256: str | None = None
    missing_reasons: list[str] = Field(default_factory=list)
    semantic_profile: ArtifactSemanticProfile | None = None
    semantic_gaps: list[str] = Field(default_factory=list)
    safe_to_use_as_evidence: bool = False


class ArtifactRuntimeLookupResult(AIpinhoModel):
    status: str
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    count: int = 0
