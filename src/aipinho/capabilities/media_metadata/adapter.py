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
        return self.capability.payload_for_boundary(file_path=file_path, entity_ref=task.entity_ref)

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
