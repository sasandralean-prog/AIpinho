from __future__ import annotations

from pathlib import Path

from aipinho.capabilities.media_metadata.adapter import MediaMetadataObserverAdapter
from aipinho.capabilities.media_metadata.backends import NativeMinimalMediaProbeBackend
from aipinho.capabilities.media_metadata.policy import MediaMetadataBackendPolicy, MediaMetadataCapability
from aipinho.schemas.artifacts.contract_perception import ObservationTask


def _minimal_frame() -> bytes:
    return bytes([0xFF, 0xFB, 0x90, 0x64]) + b"\0" * 64


def test_media_metadata_probe_consumes_governed_entity_and_produces_evidence_ref(tmp_path: Path) -> None:
    sample = tmp_path / "sample.media"
    sample.write_bytes(_minimal_frame())
    adapter = MediaMetadataObserverAdapter(
        capability=MediaMetadataCapability(
            backend_policy=MediaMetadataBackendPolicy(primary="native_minimal", fallbacks=[], min_confidence=0.6),
            backends={"native_minimal": NativeMinimalMediaProbeBackend()},
        )
    )
    task = ObservationTask(
        goal_id="goal_media_metadata",
        strategy_id="strategy_execute_observer",
        capability_id="media_metadata_reader",
        entity_ref={
            "entity_id": "entity_audio",
            "entity_role": "media_asset_candidate",
            "source_root_role": "library_root",
            "path": str(sample),
        },
        attribute_name="codec",
        canonical_key="codec",
        inputs={
            "file_path": str(sample),
            "entity_role": "media_asset_candidate",
            "source_root_role": "library_root",
            "required_confidence": 0.0,
        },
        expected_outputs=["codec", "container"],
        expected_evidence=["media_metadata_evidence"],
        status="READY_FOR_OBSERVER",
    )

    payload = adapter.execute(task, task)

    assert payload["media_metadata_capability"]["status"] == "partial"
    assert payload["observations"]
    assert all(item["capability_id"] == "media_metadata_reader" for item in payload["observations"])
    assert all(item["raw_ref"] == str(sample) for item in payload["observations"])


def test_media_metadata_probe_rejects_unauthorized_root(tmp_path: Path) -> None:
    sample = tmp_path / "sample.media"
    sample.write_bytes(_minimal_frame())
    adapter = MediaMetadataObserverAdapter()
    task = ObservationTask(
        goal_id="goal_media_metadata",
        strategy_id="strategy_execute_observer",
        capability_id="media_metadata_reader",
        entity_ref={"entity_id": "entity_audio", "entity_role": "media_asset_candidate", "source_root_role": "project_root"},
        attribute_name="codec",
        canonical_key="codec",
        inputs={"file_path": str(sample), "entity_role": "media_asset_candidate", "source_root_role": "project_root"},
        expected_outputs=["codec"],
        expected_evidence=["media_metadata_evidence"],
        status="READY_FOR_OBSERVER",
    )

    try:
        adapter.execute(task, task)
    except ValueError as exc:
        assert str(exc) == "MEDIA_CAPABILITY_ROOT_ROLE_REJECTED"
    else:
        raise AssertionError("media metadata probe accepted an unauthorized root")
