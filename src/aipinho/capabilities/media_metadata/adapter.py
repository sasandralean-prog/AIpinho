from __future__ import annotations

from typing import Any

from aipinho.capabilities.media_metadata.policy import MediaMetadataCapability
from aipinho.schemas.artifacts.contract_perception import ObservationTask, ObserverBinding


class MediaMetadataObserverAdapter:
    observer_id = "media_metadata_reader"
    version = "1"

    def __init__(self, capability: MediaMetadataCapability | None = None) -> None:
        self.capability = capability or MediaMetadataCapability()

    def execute(self, task: ObservationTask, binding: ObserverBinding) -> dict[str, Any]:
        self._ensure_eligible(task)
        file_path = str(task.inputs.get("file_path") or "")
        requested_keys = task.inputs.get("requested_canonical_keys")
        if not isinstance(requested_keys, list):
            requested_keys = (task.created_from or {}).get("requested_canonical_keys")
        if not isinstance(requested_keys, list):
            requested_keys = list(task.expected_outputs or [])
        availability_snapshot = task.inputs.get("media_metadata_backend_availability_snapshot")
        media_observation_demand = task.inputs.get("media_observation_demand")
        if not isinstance(media_observation_demand, dict):
            media_observation_demand = (task.created_from or {}).get("media_observation_demand")
        return self.capability.payload_for_boundary(
            file_path=file_path,
            entity_ref=task.entity_ref,
            requested_keys=[str(item) for item in requested_keys or []],
            backend_availability_snapshot=availability_snapshot if isinstance(availability_snapshot, dict) else None,
            media_observation_demand=media_observation_demand if isinstance(media_observation_demand, dict) else None,
        )

    def _ensure_eligible(self, task: ObservationTask) -> None:
        entity_role = str(task.inputs.get("entity_role") or task.entity_ref.get("entity_role") or "")
        source_root_role = str(task.inputs.get("source_root_role") or task.entity_ref.get("source_root_role") or "")
        file_path = str(task.inputs.get("file_path") or "")
        if entity_role not in {"media_asset_candidate", "audio_track_candidate"}:
            raise ValueError("MEDIA_CAPABILITY_ENTITY_ROLE_REJECTED")
        if source_root_role not in {"library_root", "corpus_root"}:
            raise ValueError("MEDIA_CAPABILITY_ROOT_ROLE_REJECTED")
        if not file_path:
            raise ValueError("MEDIA_CAPABILITY_FILE_PATH_MISSING")
