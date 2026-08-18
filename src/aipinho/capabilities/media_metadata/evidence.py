from __future__ import annotations

from aipinho.capabilities.media_metadata.descriptor import MediaMetadataBackendPolicy, RawMediaMetadataResult
from aipinho.capabilities.media_metadata.normalizer import MediaMetadataNormalizer
from aipinho.schemas.artifacts.contract_perception import EvidenceSet


def media_metadata_evidence_set(
    *,
    raw_results: list[RawMediaMetadataResult],
    policy: MediaMetadataBackendPolicy | None = None,
    observer_id: str = "media_metadata_reader",
) -> EvidenceSet:
    """Compile backend observations into canonical evidence records."""

    entity_ref = next((result.entity_ref for result in raw_results if result.entity_ref), {})
    return MediaMetadataNormalizer(policy=policy).normalize(
        raw_results=raw_results,
        entity_ref=entity_ref,
        observer_id=observer_id,
    )
