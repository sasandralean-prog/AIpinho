from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.artifacts.contract_perception import ObservationCapability
from aipinho.schemas.common.base import AIpinhoModel


MediaMetadataBackendStatus = Literal["available", "unavailable", "partial", "test_only", "disabled"]
MediaMetadataBackendType = Literal["python_library", "external_cli", "native_minimal", "fake"]


MEDIA_METADATA_CANONICAL_KEYS = [
    "codec",
    "container",
    "bitrate",
    "sample_rate",
    "channels",
    "duration",
    "artwork",
    "metadata",
]

MEDIA_METADATA_OBSERVABLE_KEYS = [
    *MEDIA_METADATA_CANONICAL_KEYS,
    "bitrate_bps",
    "sample_rate_hz",
    "duration_ms",
    "artwork_present",
    "metadata_status",
    "metadata_source",
    "probe_status",
]


class MediaMetadataBackendError(AIpinhoModel):
    error_id: str = Field(default_factory=lambda: f"media_backend_error_{uuid4().hex}")
    code: str
    message: str
    backend_id: str | None = None
    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class MediaMetadataBackendLimitations(AIpinhoModel):
    backend_id: str
    limitations: list[str] = Field(default_factory=list)
    unsupported_attributes: list[str] = Field(default_factory=list)
    confidence_notes: list[str] = Field(default_factory=list)


class MediaMetadataBackendDescriptor(AIpinhoModel):
    backend_id: str
    backend_type: MediaMetadataBackendType
    version: str = "1"
    supported_extensions: list[str] = Field(default_factory=list)
    supported_containers: list[str] = Field(default_factory=list)
    supported_attributes: list[str] = Field(default_factory=list)
    requires_external_binary: bool = False
    requires_python_dependency: bool = False
    dependency_name: str | None = None
    dependency_version: str | None = None
    confidence_profile: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    status: MediaMetadataBackendStatus = "unavailable"


class MediaMetadataBackendPolicy(AIpinhoModel):
    capability_id: str = "media_metadata_reader"
    strategy: str = "primary_then_fallback"
    primary: str = "mutagen"
    fallbacks: list[str] = Field(default_factory=lambda: ["ffprobe", "native_minimal"])
    allow_partial_evidence: bool = True
    min_confidence: float = 0.7
    fail_on_no_evidence: bool = True
    record_backend_limitations: bool = True


class RawMediaMetadataField(AIpinhoModel):
    canonical_key: str
    raw_value: Any | None = None
    normalized_value: Any | None = None
    confidence: float = 0.0
    semantic_type: str | None = None
    source_backend_id: str | None = None
    limitations: list[str] = Field(default_factory=list)
    raw_ref: str | None = None


class RawMediaMetadataResult(AIpinhoModel):
    result_id: str = Field(default_factory=lambda: f"raw_media_metadata_{uuid4().hex}")
    backend_id: str
    backend_version: str = "1"
    file_ref: str | None = None
    entity_ref: dict[str, Any] = Field(default_factory=dict)
    container: Any | None = None
    codec: Any | None = None
    bitrate: Any | None = None
    sample_rate: Any | None = None
    channels: Any | None = None
    duration: Any | None = None
    artwork: Any | None = None
    metadata: Any | None = None
    raw_fields: list[RawMediaMetadataField] = Field(default_factory=list)
    confidence_by_field: dict[str, float] = Field(default_factory=dict)
    limitations_by_field: dict[str, list[str]] = Field(default_factory=dict)
    errors: list[MediaMetadataBackendError] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    raw_ref: str | None = None


class MediaMetadataObservationResult(AIpinhoModel):
    capability_id: str = "media_metadata_reader"
    backend_policy: MediaMetadataBackendPolicy = Field(default_factory=MediaMetadataBackendPolicy)
    selected_backend: str | None = None
    attempted_backends: list[str] = Field(default_factory=list)
    raw_results: list[RawMediaMetadataResult] = Field(default_factory=list)
    errors: list[MediaMetadataBackendError] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    evidence_records: list[dict[str, Any]] = Field(default_factory=list)
    status: str = "blocked"


class MediaMetadataCapabilityDescriptor(AIpinhoModel):
    capability: ObservationCapability
    backend_policy: MediaMetadataBackendPolicy = Field(default_factory=MediaMetadataBackendPolicy)
    backends: list[MediaMetadataBackendDescriptor] = Field(default_factory=list)


def media_metadata_capability_descriptor(*, status: str = "available", backend_policy: MediaMetadataBackendPolicy | None = None) -> ObservationCapability:
    policy = backend_policy or MediaMetadataBackendPolicy()
    return ObservationCapability(
        capability_id="media_metadata_reader",
        name="Media metadata reader",
        version="1",
        domain="media_metadata",
        produces=list(MEDIA_METADATA_OBSERVABLE_KEYS),
        consumes=["media_asset_candidate", "file_path"],
        observable_attributes=list(MEDIA_METADATA_OBSERVABLE_KEYS),
        supported_attribute_names=list(MEDIA_METADATA_OBSERVABLE_KEYS),
        compatible_entity_kinds=["file"],
        supported_entity_types=["file"],
        evidence_types=["media_metadata_evidence"],
        preconditions=[
            "media_asset_candidate_hypothesis",
            "source_root_role_library_or_corpus",
            "file_path_present",
            "file_exists",
            "read_access",
        ],
        supported_strategies=["execute_observer"],
        typical_confidence=policy.min_confidence,
        confidence_profile={"min_confidence": policy.min_confidence, "field_level_confidence": True},
        cost_profile={"estimated": 0.4},
        latency_profile={"estimated_ms": 100},
        determinism="deterministic",
        risk_level="low",
        requires_approval=False,
        observer_binding={
            "observer_id": "media_metadata_reader",
            "adapter_id": "media_metadata_reader",
            "version": "1",
            "input_schema": {"required": ["file_path", "entity_role", "source_root_role"]},
            "output_schema": {"required": ["observations"]},
            "acquisition_method": "media_metadata_parse",
            "timeout_ms": 30000,
        },
        status=status,
        limitations=[
            "Backends are observational mechanisms; Runtime validation still depends on EvidenceRecord and coverage.",
            "Supported extensions are descriptive backend capabilities, not entity-selection rules.",
        ],
        suggested_priority=5,
        available=status == "available",
    )
