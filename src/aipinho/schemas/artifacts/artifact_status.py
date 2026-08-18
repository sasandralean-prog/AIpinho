from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class ArtifactWriterStatus(AIpinhoModel):
    status: str
    service: str = "artifact_writer"
    enabled: bool = True
    mode: str = "preview_only"
    write_enabled: bool = False
    overwrite_execution_enabled: bool = False
    source_code_targets_blocked: bool = True
    approval_required_for_future_write: bool = True
    allowed_extensions: list[str] = Field(default_factory=list)
    blocked_extensions: list[str] = Field(default_factory=list)
    allowed_base_dirs: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
