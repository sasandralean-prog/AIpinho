from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


MediaBridgeStatus = Literal[
    "completed",
    "completed_with_warnings",
    "blocked",
    "failed",
    "preview_created",
]


class PinhoForgeMediaArtifact(AIpinhoModel):
    artifact_id: str | None = None
    filename: str
    content_type: str
    size_bytes: int = 0
    output_path_sanitized: str | None = None
    status: Literal["ready", "degraded", "blocked"] = "ready"
    requires_token: bool = True
    download_endpoint: str = "/api/v1/agents/artifacts/{artifact_id}/download"


class PinhoForgeImageOperationSpec(AIpinhoModel):
    operation_id: str = Field(default_factory=lambda: f"imgop_{uuid4().hex}")
    type: str
    parameters: dict[str, str] = Field(default_factory=dict)
    risk_level: str = "safe"
    experimental: bool = False
    requires_preview: bool = False


class PinhoForgeImageRequest(AIpinhoModel):
    request_id: str = Field(default_factory=lambda: f"pinhoforge_image_{uuid4().hex}")
    operation: Literal["list_capabilities", "open_image", "apply_operations", "export_image", "generate_report"]
    session_id: str | None = None
    run_id: str | None = None
    trace_id: str | None = None
    caller_agent_id: str | None = None
    input_artifact_id: str | None = None
    input_path: str | None = None
    source_scope: str = "registered_workspace"
    operations: list[PinhoForgeImageOperationSpec] = Field(default_factory=list)
    output_format: str = "png"
    requested_output_name: str | None = None
    bridge_output_path: str | None = None
    model_review_policy: str = "none"
    timeout_seconds: int = 30
    metadata: dict[str, Any] = Field(default_factory=dict)


class PinhoForgeImageResult(AIpinhoModel):
    request_id: str
    provider_id: str = "pinhoforge_studio"
    module: str = "image_lab"
    operation: str
    status: MediaBridgeStatus
    reason_code: str | None = None
    human_message: str
    capabilities: list[str] = Field(default_factory=list)
    supported_input_formats: list[str] = Field(default_factory=list)
    supported_output_formats: list[str] = Field(default_factory=list)
    input_metadata: dict[str, Any] | None = None
    operations_applied: list[dict[str, Any]] = Field(default_factory=list)
    output_ref: str | None = None
    output_path_redacted: str | None = None
    artifact: PinhoForgeMediaArtifact | None = None
    artifacts: list[PinhoForgeMediaArtifact] = Field(default_factory=list)
    report_markdown: str | None = None
    report_json: dict[str, Any] | None = None
    model_review_recommended: bool = False
    model_review_result: dict[str, Any] | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class PinhoForge3DPrimitiveSpec(AIpinhoModel):
    primitive_id: str = Field(default_factory=lambda: f"prim_{uuid4().hex}")
    type: str
    name: str = ""
    position: dict[str, float] = Field(default_factory=dict)
    rotation: dict[str, float] = Field(default_factory=dict)
    scale: dict[str, float] = Field(default_factory=dict)
    material_color: str | None = None


class PinhoForge3DRequest(AIpinhoModel):
    request_id: str = Field(default_factory=lambda: f"pinhoforge_3d_{uuid4().hex}")
    operation: Literal["list_capabilities", "create_scene", "add_primitive", "edit_transform", "edit_material", "edit_light", "edit_camera", "export_scene", "generate_report"]
    session_id: str | None = None
    run_id: str | None = None
    trace_id: str | None = None
    caller_agent_id: str | None = None
    scene_title: str = "Untitled 3D Scene"
    scene_ref: str | None = None
    primitive_specs: list[PinhoForge3DPrimitiveSpec] = Field(default_factory=list)
    output_format: str = "obj"
    requested_output_name: str | None = None
    bridge_output_path: str | None = None
    material_color: str | None = None
    light_intensity: float | None = None
    camera_fov: float | None = None
    timeout_seconds: int = 45
    metadata: dict[str, Any] = Field(default_factory=dict)


class PinhoForge3DResult(AIpinhoModel):
    request_id: str
    provider_id: str = "pinhoforge_studio"
    module: str = "3d_lab"
    operation: str
    status: MediaBridgeStatus
    reason_code: str | None = None
    human_message: str
    capabilities: list[str] = Field(default_factory=list)
    supported_export_formats: list[str] = Field(default_factory=list)
    scene_id: str | None = None
    scene_summary: dict[str, Any] | None = None
    primitives: list[dict[str, Any]] = Field(default_factory=list)
    export_format: str | None = None
    output_ref: str | None = None
    output_path_redacted: str | None = None
    artifact: PinhoForgeMediaArtifact | None = None
    artifacts: list[PinhoForgeMediaArtifact] = Field(default_factory=list)
    report_markdown: str | None = None
    report_json: dict[str, Any] | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
