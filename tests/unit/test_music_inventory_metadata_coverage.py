from __future__ import annotations

from pathlib import Path

from aipinho.services.artifacts.observed_entity_compilation_service import ObservedEntityCompilationService
from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import ReadonlyAnalysisArtifactRuntimeService


def _minimal_frame() -> bytes:
    return bytes([0xFF, 0xFB, 0x90, 0x64]) + b"\0" * 64


def _render_for_library(tmp_path: Path, payload: bytes):
    project = tmp_path / "app"
    library = tmp_path / "library"
    project.mkdir()
    library.mkdir()
    (library / "Track.mp3").write_bytes(payload)
    observed = ObservedEntityCompilationService()
    graph = observed.compile(
        workspace=str(project),
        workspace_context={"project_root": str(project), "library_roots": [str(library)]},
    ).model_dump(mode="json")
    runtime = ReadonlyAnalysisArtifactRuntimeService(observed_entities=observed)
    contract = runtime.artifact_semantic_contracts.compile_contract(
        logical_path="reports/media/music_inventory.csv",
        content_type="text/csv",
    )
    contract["workspace_context"] = {"project_root": str(project), "library_roots": [str(library)]}
    contract["perception_compile_policy"] = {
        "mode": "full_compile",
        "execute_observers": True,
        "max_observer_executions": 10,
    }
    return runtime._contract_tabular_collection_content(
        expected_schema=contract["expected_schema"],
        request_text="Inventariar biblioteca de audio com evidencias.",
        analysis_payload={"observed_entity_graph": graph},
        declared_contract=contract,
    )


def test_metadata_probe_coverage_does_not_satisfy_identity_without_claim_evidence(tmp_path: Path) -> None:
    render = _render_for_library(tmp_path, _minimal_frame())

    metadata = render.schema_coverage["metadata_coverage_summary"]
    sufficiency = render.schema_coverage["inventory_sufficiency_summary"]
    assert render.safe_to_use is False
    assert metadata["files_attempted"] == 1
    assert metadata["files_succeeded"] == 0
    assert metadata["status"] == "partial"
    assert metadata["semantic_identity_evidence_counts"] == {
        "track_title": 0,
        "artist": 0,
        "album": 0,
        "album_artist": 0,
    }
    assert sufficiency["status"] == "blocked"
    assert sufficiency["reason_code"] == "MEDIA_PRIMARY_IDENTITY_EVIDENCE_INSUFFICIENT"
    assert "MEDIA_IDENTITY_EVIDENCE_INSUFFICIENT" not in sufficiency["reason_codes"]
    assert sufficiency["use_safety"]["phase1_discovery"] is False
    assert sufficiency["use_safety"]["full_truth_claim"] is False
    assert "media_metadata_capability_blocked" in render.content
    assert "executed" in render.content


def test_metadata_probe_incomplete_blocks_with_specific_reason(tmp_path: Path) -> None:
    render = _render_for_library(tmp_path, b"not a media header")

    metadata = render.schema_coverage["metadata_coverage_summary"]
    sufficiency = render.schema_coverage["inventory_sufficiency_summary"]
    assert render.safe_to_use is False
    assert render.reason_code == "MEDIA_PRIMARY_IDENTITY_EVIDENCE_INSUFFICIENT"
    assert metadata["files_attempted"] == 1
    assert metadata["files_succeeded"] == 0
    assert sufficiency["reason_code"] == "MEDIA_PRIMARY_IDENTITY_EVIDENCE_INSUFFICIENT"
    assert "MEDIA_METADATA_OBSERVATION_INCOMPLETE" in sufficiency["reason_codes"]
