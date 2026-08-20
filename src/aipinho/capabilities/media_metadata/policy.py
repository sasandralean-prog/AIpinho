from __future__ import annotations

from typing import Any

from aipinho.capabilities.media_metadata.backends import (
    FFprobeMediaMetadataBackend,
    MutagenMediaMetadataBackend,
    NativeMinimalMediaProbeBackend,
)
from aipinho.capabilities.media_metadata.descriptor import (
    MEDIA_METADATA_CANONICAL_KEYS,
    MEDIA_METADATA_EVIDENCE_KEYS,
    MediaMetadataBackendError,
    MediaMetadataBackendPolicy,
    MediaMetadataObservationResult,
    RawMediaMetadataResult,
)
from aipinho.capabilities.media_metadata.normalizer import MediaMetadataNormalizer


class MediaMetadataCapability:
    """Semantic media metadata capability owned by AIpinho."""

    def __init__(self, *, backend_policy: MediaMetadataBackendPolicy | None = None, backends: dict[str, Any] | None = None) -> None:
        self.backend_policy = backend_policy or MediaMetadataBackendPolicy()
        self.backends = backends or {
            "mutagen": MutagenMediaMetadataBackend(),
            "ffprobe": FFprobeMediaMetadataBackend(),
            "native_minimal": NativeMinimalMediaProbeBackend(),
        }
        self.normalizer = MediaMetadataNormalizer(policy=self.backend_policy)

    def observe(self, *, file_path: str, entity_ref: dict[str, Any]) -> MediaMetadataObservationResult:
        attempted: list[str] = []
        raw_results: list[RawMediaMetadataResult] = []
        observed_keys: set[str] = set()
        selected_backend: str | None = None
        for backend_id in self._backend_order():
            backend = self.backends.get(backend_id)
            if backend is None:
                raw_results.append(
                    RawMediaMetadataResult(
                        backend_id=backend_id,
                        file_ref=file_path,
                        entity_ref=entity_ref,
                        errors=[
                            MediaMetadataBackendError(
                                code="MEDIA_BACKEND_NOT_AVAILABLE",
                                message="Backend is not registered.",
                                backend_id=backend_id,
                            )
                        ],
                    )
                )
                attempted.append(backend_id)
                continue
            attempted.append(backend_id)
            result = backend.probe(file_path=file_path, entity_ref=entity_ref)
            raw_results.append(result)
            keys = {
                field.canonical_key
                for field in result.raw_fields
                if field.normalized_value not in (None, "")
            }
            if keys and selected_backend is None:
                selected_backend = result.backend_id
            observed_keys.update(keys)
            if self.backend_policy.strategy == "primary_then_fallback" and not self.backend_policy.allow_partial_evidence and keys:
                break
            if set(MEDIA_METADATA_CANONICAL_KEYS).issubset(observed_keys):
                break
        payload = self.normalizer.observations_payload(
            raw_results=raw_results,
            entity_ref=entity_ref,
            observer_id="media_metadata_reader",
            capability_id="media_metadata_reader",
        )
        errors = [error for result in raw_results for error in result.errors]
        limitations = [
            limitation
            for result in raw_results
            for limitations in result.limitations_by_field.values()
            for limitation in limitations
        ]
        status = "partial" if payload["observations"] else "blocked"
        if not payload["observations"] and self.backend_policy.fail_on_no_evidence and not errors:
            errors.append(
                MediaMetadataBackendError(
                    code="MEDIA_BACKEND_NO_EVIDENCE",
                    message="No backend produced valid media metadata evidence.",
                    backend_id=selected_backend,
                )
            )
        return MediaMetadataObservationResult(
            backend_policy=self.backend_policy,
            selected_backend=selected_backend,
            attempted_backends=attempted,
            raw_results=raw_results,
            errors=errors,
            limitations=limitations,
            evidence_records=payload["observations"],
            status=status,
        )

    def payload_for_boundary(self, *, file_path: str, entity_ref: dict[str, Any]) -> dict[str, Any]:
        observation = self.observe(file_path=file_path, entity_ref=entity_ref)
        successful_backends = sorted({
            record.get("backend_id")
            for record in observation.evidence_records
            if record.get("backend_id")
        })
        error_counts: dict[str, int] = {}
        for error in observation.errors:
            error_counts[error.code] = error_counts.get(error.code, 0) + 1
        return {
            "raw_ref": file_path,
            "observations": observation.evidence_records,
            "media_metadata_capability": {
                "status": observation.status,
                "capability_id": "media_metadata_reader",
                "primary_backend": self.backend_policy.primary,
                "selected_backend": observation.selected_backend,
                "attempted_backends": list(observation.attempted_backends),
                "successful_backends": successful_backends,
                "fallback_backends_used": [
                    backend for backend in successful_backends
                    if backend != self.backend_policy.primary
                ],
                "available_backends": [
                    result.backend_id for result in observation.raw_results if not result.errors
                ],
                "blocked_backends": [
                    result.backend_id for result in observation.raw_results if result.errors
                ],
                "missing_dependency": [
                    self._dependency_name(error.code, error.backend_id)
                    for error in observation.errors
                    if "NOT_AVAILABLE" in error.code or "NOT_IMPORTABLE" in error.code or "DEPENDENCY" in error.code
                ],
                "evidence_records_created": len(observation.evidence_records),
                "attributes_observed": sorted({record["canonical_key"] for record in observation.evidence_records if record.get("canonical_key")}),
                "attributes_missing": [
                    key for key in MEDIA_METADATA_EVIDENCE_KEYS
                    if key not in {record.get("canonical_key") for record in observation.evidence_records}
                ],
                "backend_error_counts": error_counts,
                "limitations": observation.limitations,
                "errors": [error.model_dump(mode="json") for error in observation.errors],
            },
        }

    def _backend_order(self) -> list[str]:
        return list(dict.fromkeys([self.backend_policy.primary, *self.backend_policy.fallbacks]))

    def _dependency_name(self, code: str, backend_id: str | None) -> str:
        if code == "MUTAGEN_NOT_IMPORTABLE":
            return "mutagen"
        if code == "FFPROBE_NOT_AVAILABLE":
            return "ffprobe"
        return backend_id or code
