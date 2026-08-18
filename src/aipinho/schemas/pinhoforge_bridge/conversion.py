from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


ConversionProviderStatus = Literal[
    "completed",
    "preview_created",
    "blocked",
    "failed",
]


class PinhoForgeConversionRequest(AIpinhoModel):
    request_id: str = Field(default_factory=lambda: f"pinhoforge_conversion_{uuid4().hex}")
    operation: Literal["list_capabilities", "dry_run", "execute"]
    input_path: str | None = None
    input_display_name: str | None = None
    detected_format: str | None = None
    target_format: str | None = None
    source_scope: str = "registered_workspace"
    bridge_output_path: str | None = None
    requested_output_name: str | None = None
    allow_semantic_conversion: bool = False
    allow_experimental_conversion: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class PinhoForgeConversionArtifact(AIpinhoModel):
    artifact_id: str | None = None
    filename: str
    content_type: str = "application/octet-stream"
    size_bytes: int
    output_path_sanitized: str | None = None
    requires_token: bool = True
    download_endpoint: str = "/api/v1/artifacts/{artifact_id}/download"
    status: Literal["ready", "degraded", "blocked"] = "ready"


class PinhoForgeConversionResult(AIpinhoModel):
    request_id: str
    provider_id: str = "pinhoforge_studio"
    operation: str
    status: ConversionProviderStatus
    reason_code: str | None = None
    human_message: str
    capabilities: list[dict[str, Any]] = Field(default_factory=list)
    route: dict[str, Any] | None = None
    dry_run: dict[str, Any] | None = None
    artifact: PinhoForgeConversionArtifact | None = None
    logs_sanitized: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    raw_hidden_by_default: bool = True
