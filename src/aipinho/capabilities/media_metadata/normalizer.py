from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from aipinho.capabilities.media_metadata.descriptor import (
    MEDIA_METADATA_CANONICAL_KEYS,
    MediaMetadataBackendPolicy,
    RawMediaMetadataField,
    RawMediaMetadataResult,
)
from aipinho.schemas.artifacts.contract_perception import EvidenceRecord, EvidenceSet


class MediaMetadataNormalizer:
    """Canonical media metadata normalizer.

    Backends can vary. This class is the stable AIpinho contract that turns
    RawMediaMetadataResult into EvidenceRecord objects.
    """

    def __init__(self, policy: MediaMetadataBackendPolicy | None = None) -> None:
        self.policy = policy or MediaMetadataBackendPolicy()

    def normalize(
        self,
        *,
        raw_results: list[RawMediaMetadataResult],
        entity_ref: dict[str, Any],
        observer_id: str = "media_metadata_reader",
        capability_id: str = "media_metadata_reader",
    ) -> EvidenceSet:
        records: list[EvidenceRecord] = []
        for result in raw_results:
            for field in result.raw_fields:
                record = self._record_for_field(
                    result=result,
                    field=field,
                    entity_ref=entity_ref or result.entity_ref,
                    observer_id=observer_id,
                    capability_id=capability_id,
                )
                if record is not None:
                    records.append(record)
        confidence_values = [item.confidence for item in records]
        return EvidenceSet(
            records=records,
            entity_refs=[item.entity_ref for item in records if item.entity_ref],
            attribute_names=sorted({str(item.attribute_name) for item in records if item.attribute_name}),
            canonical_keys=sorted({str(item.canonical_key) for item in records if item.canonical_key}),
            coverage_summary={
                "observed_record_count": len(records),
                "observed_attribute_count": len({item.attribute_name for item in records if item.attribute_name}),
                "observed_canonical_key_count": len({item.canonical_key for item in records if item.canonical_key}),
                "attempted_backend_count": len(raw_results),
            },
            confidence_summary={
                "average_confidence": round(sum(confidence_values) / len(confidence_values), 4) if confidence_values else 0.0,
                "minimum_confidence": min(confidence_values) if confidence_values else 0.0,
                "maximum_confidence": max(confidence_values) if confidence_values else 0.0,
            },
        )

    def observations_payload(
        self,
        *,
        raw_results: list[RawMediaMetadataResult],
        entity_ref: dict[str, Any],
        observer_id: str = "media_metadata_reader",
        capability_id: str = "media_metadata_reader",
    ) -> dict[str, Any]:
        evidence_set = self.normalize(
            raw_results=raw_results,
            entity_ref=entity_ref,
            observer_id=observer_id,
            capability_id=capability_id,
        )
        return {
            "raw_ref": next((item.raw_ref for item in raw_results if item.raw_ref), None),
            "observations": [
                record.model_dump(mode="json")
                for record in evidence_set.records
            ],
            "media_metadata_capability": {
                "status": "partial" if evidence_set.records else "blocked",
                "capability_id": capability_id,
                "selected_backend": next((item.backend_id for item in raw_results if item.raw_fields), None),
                "available_backends": [item.backend_id for item in raw_results if not item.errors],
                "blocked_backends": [item.backend_id for item in raw_results if item.errors],
                "missing_dependency": [
                    self._dependency_name(error.code, result.backend_id)
                    for result in raw_results
                    for error in result.errors
                    if "NOT_AVAILABLE" in error.code or "NOT_IMPORTABLE" in error.code or "DEPENDENCY" in error.code
                ],
                "evidence_records_created": len(evidence_set.records),
                "attributes_observed": evidence_set.canonical_keys,
                "attributes_missing": [
                    key for key in MEDIA_METADATA_CANONICAL_KEYS if key not in set(evidence_set.canonical_keys)
                ],
                "limitations": [
                    limitation
                    for result in raw_results
                    for limitations in result.limitations_by_field.values()
                    for limitation in limitations
                ],
            },
        }

    def _record_for_field(
        self,
        *,
        result: RawMediaMetadataResult,
        field: RawMediaMetadataField,
        entity_ref: dict[str, Any],
        observer_id: str,
        capability_id: str,
    ) -> EvidenceRecord | None:
        canonical_key = self._canonical_key(field.canonical_key)
        if canonical_key not in MEDIA_METADATA_CANONICAL_KEYS:
            return None
        normalized = self._normalize_value(canonical_key, field.normalized_value if field.normalized_value is not None else field.raw_value)
        if normalized in (None, ""):
            return None
        confidence = float(result.confidence_by_field.get(canonical_key, field.confidence or 0.0))
        if confidence < self.policy.min_confidence:
            return None
        raw_ref = field.raw_ref or result.raw_ref or result.file_ref
        return EvidenceRecord(
            source="media_file",
            acquisition_method="media_metadata_parse",
            observer_id=observer_id,
            capability_id=capability_id,
            backend_id=result.backend_id,
            entity_ref=entity_ref,
            attribute_name=canonical_key,
            canonical_key=canonical_key,
            raw_ref=raw_ref,
            normalized_value=normalized,
            semantic_type=field.semantic_type or self._semantic_type(canonical_key),
            confidence=confidence,
            provenance={
                "backend_id": result.backend_id,
                "backend_version": result.backend_version,
                "file_ref": result.file_ref,
                "raw_result_id": result.result_id,
                "normalizer": "MediaMetadataNormalizer",
            },
            timestamp=datetime.now(timezone.utc).isoformat(),
            ambiguity=0.0,
            contradictions=[],
            limitations=[
                *field.limitations,
                *result.limitations_by_field.get(canonical_key, []),
            ],
        )

    def _canonical_key(self, value: Any) -> str:
        text = str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")
        aliases = {
            "sample_rate_hz": "sample_rate",
            "channels_count": "channels",
            "duration_seconds": "duration",
            "duration_ms": "duration",
            "bit_rate": "bitrate",
            "bitrate_bps": "bitrate",
            "sample_rate_hz": "sample_rate",
            "embedded_artwork_presence": "artwork",
            "artwork_present": "artwork",
            "embedded_metadata": "metadata",
        }
        return aliases.get(text, text)

    def _dependency_name(self, code: str, backend_id: str | None) -> str:
        if code == "MUTAGEN_NOT_IMPORTABLE":
            return "mutagen"
        if code == "FFPROBE_NOT_AVAILABLE":
            return "ffprobe"
        return backend_id or code

    def _normalize_value(self, key: str, value: Any) -> Any | None:
        if value is None:
            return None
        if key == "duration":
            try:
                return round(float(value), 6)
            except (TypeError, ValueError):
                return None
        if key in {"bitrate", "sample_rate", "channels"}:
            try:
                return int(float(value))
            except (TypeError, ValueError):
                return None
        if key == "metadata":
            return value if isinstance(value, dict) else {"value": str(value)}
        if key == "artwork":
            text = str(value).strip()
            return text if text else None
        text = str(value).strip()
        return text.casefold() if key in {"codec", "container"} else text

    def _semantic_type(self, key: str) -> str:
        if key in {"codec", "container", "bitrate", "sample_rate", "channels", "duration"}:
            return "technical_metadata"
        if key == "artwork":
            return "embedded_assets"
        return "descriptive_metadata"
