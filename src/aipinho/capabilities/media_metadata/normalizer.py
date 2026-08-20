from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from aipinho.capabilities.media_metadata.descriptor import (
    MEDIA_METADATA_CANONICAL_KEYS,
    MEDIA_METADATA_EVIDENCE_KEYS,
    MEDIA_IDENTITY_CANONICAL_KEYS,
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
                emitted_fields = [field, *self._identity_fields_from_metadata(field=field, result=result)]
                for emitted_field in emitted_fields:
                    record = self._record_for_field(
                        result=result,
                        field=emitted_field,
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

    def _identity_fields_from_metadata(
        self,
        *,
        field: RawMediaMetadataField,
        result: RawMediaMetadataResult,
    ) -> list[RawMediaMetadataField]:
        canonical = self._canonical_key(field.canonical_key)
        if canonical != "metadata":
            return []
        source = field.normalized_value if field.normalized_value is not None else field.raw_value
        if not isinstance(source, dict):
            return []
        rows: list[RawMediaMetadataField] = []
        for raw_tag_key, raw_tag_value in source.items():
            identity_key = self._identity_key_for_raw_tag(raw_tag_key)
            if not identity_key:
                continue
            normalized_value = self._normalize_identity_value(raw_tag_value)
            if normalized_value in (None, ""):
                continue
            rows.append(
                RawMediaMetadataField(
                    canonical_key=identity_key,
                    raw_value=raw_tag_value,
                    normalized_value=normalized_value,
                    confidence=self._identity_confidence(field=field, result=result),
                    semantic_type="media_identity",
                    source_backend_id=field.source_backend_id or result.backend_id,
                    limitations=list(field.limitations),
                    raw_ref=field.raw_ref or result.raw_ref or result.file_ref,
                    provenance={
                        "raw_tag_key": str(raw_tag_key),
                        "raw_tag_value_repr": repr(raw_tag_value)[:500],
                        "semantic_mapper": "media_metadata_identity_tag_mapper_v1",
                        "canonical_key": identity_key,
                    },
                )
            )
        return rows

    def _identity_key_for_raw_tag(self, raw_key: Any) -> str | None:
        key = str(raw_key or "").strip()
        normalized = self._normalize_tag_key(key)
        aliases = {
            "title": "track_title",
            "tit2": "track_title",
            "copyright_nam": "track_title",
            "artist": "artist",
            "artists": "artist",
            "tpe1": "artist",
            "copyright_art": "artist",
            "album": "album",
            "talb": "album",
            "copyright_alb": "album",
            "albumartist": "album_artist",
            "album_artist": "album_artist",
            "albumartists": "album_artist",
            "album_artists": "album_artist",
            "tpe2": "album_artist",
            "tpe2_tp2": "album_artist",
            "aart": "album_artist",
        }
        return aliases.get(normalized)

    def _normalize_tag_key(self, raw_key: Any) -> str:
        text = str(raw_key or "").strip().casefold()
        text = text.replace("\xa9", "copyright_")
        text = text.replace("©", "copyright_")
        chars = [char if char.isalnum() else "_" for char in text]
        return "_".join(part for part in "".join(chars).split("_") if part)

    def _identity_confidence(self, *, field: RawMediaMetadataField, result: RawMediaMetadataResult) -> float:
        field_confidence = float(field.confidence or 0.0)
        metadata_confidence = result.confidence_by_field.get("metadata")
        if metadata_confidence is None:
            return field_confidence
        return min(field_confidence, float(metadata_confidence or 0.0))

    def _normalize_identity_value(self, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, (list, tuple, set)):
            parts = [self._normalize_identity_value(item) for item in value]
            text = "; ".join(part for part in parts if part)
        elif hasattr(value, "text"):
            text = self._normalize_identity_value(getattr(value, "text"))
        else:
            text = str(value)
        text = " ".join(str(text or "").strip().split())
        return text or None

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
                    key for key in MEDIA_METADATA_EVIDENCE_KEYS if key not in set(evidence_set.canonical_keys)
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
        if canonical_key not in MEDIA_METADATA_EVIDENCE_KEYS:
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
                **self._identity_provenance(canonical_key=canonical_key, field=field),
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
        if key in MEDIA_IDENTITY_CANONICAL_KEYS:
            return self._normalize_identity_value(value)
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
        if key in MEDIA_IDENTITY_CANONICAL_KEYS:
            return "media_identity"
        return "descriptive_metadata"

    def _identity_provenance(self, *, canonical_key: str, field: RawMediaMetadataField) -> dict[str, Any]:
        if canonical_key not in MEDIA_IDENTITY_CANONICAL_KEYS:
            return {}
        return {
            "raw_tag_key": str(field.provenance.get("raw_tag_key") or field.canonical_key),
            "raw_tag_value_repr": str(field.provenance.get("raw_tag_value_repr") or repr(field.raw_value)[:500]),
            "semantic_mapper": "media_metadata_identity_tag_mapper_v1",
            "canonical_key": canonical_key,
        }
