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
    MEDIA_IDENTITY_CANONICAL_KEYS,
    MediaMetadataBackendError,
    MediaMetadataBackendDescriptor,
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

    def observe(
        self,
        *,
        file_path: str,
        entity_ref: dict[str, Any],
        requested_keys: list[str] | None = None,
        backend_availability_snapshot: dict[str, Any] | None = None,
    ) -> MediaMetadataObservationResult:
        attempted: list[str] = []
        raw_results: list[RawMediaMetadataResult] = []
        observed_keys: set[str] = set()
        selected_backend: str | None = None
        requested = self._normalized_requested_keys(requested_keys)
        identity_demand = [key for key in MEDIA_IDENTITY_CANONICAL_KEYS if key in requested]
        availability_snapshot = self._coerce_availability_snapshot(backend_availability_snapshot)
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
            descriptor = availability_snapshot.get(backend_id) or self._backend_descriptor(backend)
            if str(descriptor.status) not in {"available", "partial", "test_only"}:
                raw_results.append(
                    self._unavailable_result_from_descriptor(
                        backend_id=backend_id,
                        descriptor=descriptor,
                        file_path=file_path,
                        entity_ref=entity_ref,
                    )
                )
                continue
            if not self._backend_can_change_blocking_outcome(
                descriptor=descriptor,
                requested_keys=requested,
                identity_demand=identity_demand,
                observed_keys=observed_keys,
            ):
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
            observed_keys.update(self._normalized_evidence_keys_for_result(result=result, entity_ref=entity_ref))
            if self._blocking_demand_satisfied(
                requested_keys=requested,
                identity_demand=identity_demand,
                observed_keys=observed_keys,
            ):
                break
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

    def payload_for_boundary(
        self,
        *,
        file_path: str,
        entity_ref: dict[str, Any],
        requested_keys: list[str] | None = None,
        backend_availability_snapshot: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        observation = self.observe(
            file_path=file_path,
            entity_ref=entity_ref,
            requested_keys=requested_keys,
            backend_availability_snapshot=backend_availability_snapshot,
        )
        successful_backends = sorted({
            record.get("backend_id")
            for record in observation.evidence_records
            if record.get("backend_id")
        })
        error_counts: dict[str, int] = {}
        for error in observation.errors:
            error_counts[error.code] = error_counts.get(error.code, 0) + 1
        available_backends = [
            result.backend_id for result in observation.raw_results if not result.errors
        ]
        blocked_backends = [
            result.backend_id for result in observation.raw_results if result.errors
        ]
        missing_dependency = [
            self._dependency_name(error.code, error.backend_id)
            for error in observation.errors
            if "NOT_AVAILABLE" in error.code or "NOT_IMPORTABLE" in error.code or "DEPENDENCY" in error.code
        ]
        evidence_counts_by_canonical_key: dict[str, int] = {}
        evidence_counts_by_backend: dict[str, int] = {}
        for record in observation.evidence_records:
            canonical_key = str(record.get("canonical_key") or "")
            backend_id = str(record.get("backend_id") or "")
            if canonical_key:
                evidence_counts_by_canonical_key[canonical_key] = evidence_counts_by_canonical_key.get(canonical_key, 0) + 1
            if backend_id:
                evidence_counts_by_backend[backend_id] = evidence_counts_by_backend.get(backend_id, 0) + 1
        return {
            "raw_ref": file_path,
            "observations": observation.evidence_records,
            "media_metadata_capability": {
                "status": observation.status,
                "configured": True,
                "available": bool(available_backends or observation.attempted_backends),
                "execution_status": observation.status,
                "capability_id": "media_metadata_reader",
                "primary_backend": self.backend_policy.primary,
                "selected_backend": observation.selected_backend,
                "attempted_backends": list(observation.attempted_backends),
                "successful_backends": successful_backends,
                "fallback_backends_used": [
                    backend for backend in successful_backends
                    if backend != self.backend_policy.primary
                ],
                "available_backends": available_backends,
                "blocked_backends": blocked_backends,
                "missing_dependency": missing_dependency,
                "evidence_records_created": len(observation.evidence_records),
                "evidence_counts_by_canonical_key": evidence_counts_by_canonical_key,
                "evidence_counts_by_backend": evidence_counts_by_backend,
                "semantic_identity_evidence_counts": {
                    key: evidence_counts_by_canonical_key.get(key, 0)
                    for key in MEDIA_IDENTITY_CANONICAL_KEYS
                },
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

    def backend_availability_snapshot(self) -> dict[str, dict[str, Any]]:
        snapshot: dict[str, dict[str, Any]] = {}
        for backend_id in self._backend_order():
            backend = self.backends.get(backend_id)
            if backend is None:
                snapshot[backend_id] = {
                    "backend_id": backend_id,
                    "backend_type": "fake",
                    "status": "unavailable",
                    "supported_attributes": [],
                    "dependency_name": backend_id,
                }
                continue
            snapshot[backend_id] = self._backend_descriptor(backend).model_dump(mode="json")
        return snapshot

    def _backend_descriptor(self, backend: Any) -> MediaMetadataBackendDescriptor:
        descriptor = backend.descriptor() if hasattr(backend, "descriptor") else None
        if isinstance(descriptor, MediaMetadataBackendDescriptor):
            return descriptor
        if isinstance(descriptor, dict):
            return MediaMetadataBackendDescriptor(**descriptor)
        return MediaMetadataBackendDescriptor(
            backend_id=str(getattr(backend, "backend_id", "unknown")),
            backend_type="fake",
            supported_attributes=list(MEDIA_METADATA_EVIDENCE_KEYS),
            status="available",
        )

    def _coerce_availability_snapshot(self, snapshot: dict[str, Any] | None) -> dict[str, MediaMetadataBackendDescriptor]:
        rows: dict[str, MediaMetadataBackendDescriptor] = {}
        for backend_id, value in dict(snapshot or {}).items():
            if isinstance(value, MediaMetadataBackendDescriptor):
                rows[str(backend_id)] = value
            elif isinstance(value, dict):
                rows[str(backend_id)] = MediaMetadataBackendDescriptor(**value)
        return rows

    def _normalized_requested_keys(self, keys: list[str] | None) -> set[str]:
        evidence_keys = set(MEDIA_METADATA_EVIDENCE_KEYS)
        return {
            str(key or "").strip()
            for key in keys or []
            if str(key or "").strip() in evidence_keys
        }

    def _normalized_evidence_keys_for_result(self, *, result: RawMediaMetadataResult, entity_ref: dict[str, Any]) -> set[str]:
        evidence = self.normalizer.normalize(
            raw_results=[result],
            entity_ref=entity_ref,
            observer_id="media_metadata_reader",
            capability_id="media_metadata_reader",
        )
        return {str(record.canonical_key or "") for record in evidence.records if record.canonical_key}

    def _backend_can_change_blocking_outcome(
        self,
        *,
        descriptor: MediaMetadataBackendDescriptor,
        requested_keys: set[str],
        identity_demand: list[str],
        observed_keys: set[str],
    ) -> bool:
        supported = set(descriptor.supported_attributes or [])
        if identity_demand:
            if set(identity_demand).intersection(observed_keys):
                return False
            return bool(set(identity_demand).intersection(supported))
        if requested_keys and requested_keys.issubset(observed_keys):
            return False
        return bool(not requested_keys or requested_keys.intersection(supported))

    def _blocking_demand_satisfied(
        self,
        *,
        requested_keys: set[str],
        identity_demand: list[str],
        observed_keys: set[str],
    ) -> bool:
        if identity_demand:
            return bool(set(identity_demand).intersection(observed_keys))
        return bool(requested_keys and requested_keys.issubset(observed_keys))

    def _unavailable_result_from_descriptor(
        self,
        *,
        backend_id: str,
        descriptor: MediaMetadataBackendDescriptor,
        file_path: str,
        entity_ref: dict[str, Any],
    ) -> RawMediaMetadataResult:
        code = "FFPROBE_NOT_AVAILABLE" if backend_id == "ffprobe" else "MUTAGEN_NOT_IMPORTABLE" if backend_id == "mutagen" else "MEDIA_BACKEND_NOT_AVAILABLE"
        dependency = descriptor.dependency_name or backend_id
        return RawMediaMetadataResult(
            backend_id=backend_id,
            backend_version=descriptor.version,
            file_ref=file_path,
            entity_ref=entity_ref,
            errors=[
                MediaMetadataBackendError(
                    code=code,
                    message=f"Backend dependency/state is unavailable in stage snapshot: {dependency}.",
                    backend_id=backend_id,
                )
            ],
            limitations_by_field={key: [f"{backend_id} unavailable in stage snapshot"] for key in descriptor.supported_attributes or []},
            provenance={"backend": backend_id, "file_path": file_path, "availability_snapshot": True},
            raw_ref=file_path,
        )
