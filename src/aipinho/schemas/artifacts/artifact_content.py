from __future__ import annotations

from pydantic import Field

from aipinho.schemas.artifacts.artifact_lifecycle import ArtifactFormat
from aipinho.schemas.artifacts.artifact_trace import ArtifactTraceItem
from aipinho.schemas.common.base import AIpinhoModel


class ArtifactContent(AIpinhoModel):
    content: str
    format: ArtifactFormat = "markdown"
    content_hash: str | None = None
    char_count: int = 0
    byte_count: int = 0


class ArtifactContentValidation(AIpinhoModel):
    valid: bool = False
    format: ArtifactFormat = "unknown"
    size_valid: bool = False
    secret_free: bool = False
    binary_free: bool = False
    executable_free: bool = False
    patch_payload_allowed: bool = False
    format_valid: bool = False
    blocked_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    redacted_preview: str = ""
    content_hash: str = ""
    trace: list[ArtifactTraceItem] = Field(default_factory=list)
