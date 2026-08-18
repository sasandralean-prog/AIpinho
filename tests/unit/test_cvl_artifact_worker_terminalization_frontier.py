from __future__ import annotations

from aipinho.schemas.cvl import FireTestProfile
from aipinho.services.cvl import CognitiveDependencyGraphService, CognitiveGapPredictor


def test_cvl_predicts_accepted_running_artifact_worker_terminalization_gap() -> None:
    profile = FireTestProfile(
        profile_id="profile_artifact_worker_terminalization",
        name="Accepted worker terminalization frontier",
        objective="Predict artifact worker terminality gap before runtime execution.",
        domain="generic",
        expected_pipeline=[
            "public_response_boundary",
            "accepted_running",
            "artifact_creation_started",
            "result_finalization",
        ],
        involved_contracts=["analysis_readonly", "public_runtime_response"],
        expected_capabilities=["read_workspace"],
        metadata={
            "public_response_boundary": {
                "response_mode": "accepted_running",
                "accepted_running_status": "available",
                "artifact_worker_terminalization": "missing",
                "artifact_runtime_status": "stalled_after_artifact_creation_started",
                "result_endpoint_after_artifact_start": "404",
                "confidence": 0.86,
            }
        },
    )
    graph = CognitiveDependencyGraphService().build(profile)

    report = CognitiveGapPredictor().predict(profile, graph=graph, available_capabilities=["read_workspace"])

    assert report.predicted_status == "blocked"
    assert report.probable_component == "artifact_worker_terminalization_guard"
    assert report.reason_codes == ["ACCEPTED_RUNNING_ARTIFACT_WORKER_TERMINALIZATION_GAP"]
    assert report.confidence == 0.86


def test_cvl_predicts_artifact_runtime_stalled_after_artifact_start_when_guard_metadata_is_ready() -> None:
    profile = FireTestProfile(
        profile_id="profile_artifact_runtime_stalled",
        name="Artifact runtime stalled frontier",
        objective="Predict stalled artifact runtime after accepted worker guard metadata is present.",
        domain="generic",
        expected_pipeline=[
            "public_response_boundary",
            "accepted_running",
            "artifact_started_without_terminal",
            "result_endpoint_404",
        ],
        involved_contracts=["analysis_readonly", "public_runtime_response"],
        expected_capabilities=["read_workspace"],
        metadata={
            "public_response_boundary": {
                "response_mode": "accepted_running",
                "accepted_running_status": "available",
                "artifact_worker_terminalization": "guarded",
                "artifact_runtime_status": "stalled_after_artifact_creation_started",
                "confidence": 0.84,
            }
        },
    )
    graph = CognitiveDependencyGraphService().build(profile)

    report = CognitiveGapPredictor().predict(profile, graph=graph, available_capabilities=["read_workspace"])

    assert report.predicted_status == "blocked"
    assert report.probable_component == "artifact_worker_terminalization_guard"
    assert report.reason_codes == ["ARTIFACT_RUNTIME_STALLED_AFTER_ARTIFACT_CREATION_STARTED"]


def test_cvl_predicts_legacy_artifact_registry_projection_boundary() -> None:
    profile = FireTestProfile(
        profile_id="profile_artifact_registry_projection",
        name="Artifact registry projection frontier",
        objective="Predict artifact creation exception caused by unreadable artifact registry projection.",
        domain="generic",
        expected_pipeline=[
            "public_response_boundary",
            "accepted_running",
            "artifact_creation_started",
            "artifact_registry_projection",
        ],
        involved_contracts=["analysis_readonly", "artifact_runtime"],
        expected_capabilities=["read_workspace"],
        metadata={
            "public_response_boundary": {
                "response_mode": "accepted_running",
                "accepted_running_status": "available",
                "artifact_registry_status": "legacy_invalid",
                "confidence": 0.82,
            }
        },
    )
    graph = CognitiveDependencyGraphService().build(profile)

    report = CognitiveGapPredictor().predict(profile, graph=graph, available_capabilities=["read_workspace"])

    assert report.predicted_status == "blocked"
    assert report.probable_component == "ArtifactRegistryRepository"
    assert report.reason_codes == ["ARTIFACT_REGISTRY_LEGACY_PROJECTION_UNREADABLE"]
