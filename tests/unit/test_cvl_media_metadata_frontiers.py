from aipinho.schemas.cvl import FireTestProfile
from aipinho.services.cvl import CognitiveDependencyGraphService, CognitiveGapPredictor


def test_cvl_predicts_media_inventory_coverage_insufficient_frontier() -> None:
    profile = FireTestProfile(
        profile_id="profile_media_inventory_coverage",
        name="Media inventory sufficiency coverage",
        objective="Predict inventory sufficiency before phase completion.",
        domain="generic",
        expected_pipeline=[
            "semantic_artifact_contract",
            "media_metadata_observation",
            "media_inventory_sufficiency",
            "phase_semantic_completion",
        ],
        involved_contracts=["media_corpus_inventory_contract"],
        expected_capabilities=["media_metadata_reader"],
        metadata={
            "inventory_sufficiency": {
                "status": "blocked",
                "coverage_status": "insufficient",
                "reason_code": "MEDIA_INVENTORY_COVERAGE_INSUFFICIENT",
                "safe_to_use": False,
                "confidence": 0.89,
            },
            "metadata_coverage": {
                "status": "satisfied",
                "files_expected": 10,
                "files_succeeded": 10,
            },
        },
    )
    graph = CognitiveDependencyGraphService().build(profile)

    report = CognitiveGapPredictor().predict(
        profile,
        graph=graph,
        available_capabilities=["media_metadata_reader"],
    )

    assert report.predicted_status == "blocked"
    assert report.probable_component == "media_inventory_sufficiency"
    assert report.reason_codes == ["MEDIA_INVENTORY_COVERAGE_INSUFFICIENT"]
    assert report.confidence == 0.89


def test_cvl_predicts_media_metadata_probe_required_frontier() -> None:
    profile = FireTestProfile(
        profile_id="profile_media_metadata_probe_required",
        name="Media metadata probe required",
        objective="Predict missing governed metadata probe before artifact truth.",
        domain="generic",
        expected_pipeline=[
            "semantic_artifact_contract",
            "media_metadata_observation",
            "media_inventory_sufficiency",
        ],
        involved_contracts=["media_corpus_inventory_contract"],
        expected_capabilities=["media_metadata_reader"],
        metadata={
            "metadata_coverage": {
                "status": "not_run",
                "files_expected": 4,
                "files_attempted": 0,
                "confidence": 0.85,
            },
            "media_metadata_capability": {
                "capability_id": "media_metadata_reader",
                "capability_status": "registered",
                "backend_status": "available",
            },
        },
    )
    graph = CognitiveDependencyGraphService().build(profile)

    report = CognitiveGapPredictor().predict(
        profile,
        graph=graph,
        available_capabilities=["media_metadata_reader"],
    )

    assert report.predicted_status == "blocked"
    assert report.probable_component == "media_metadata_observation"
    assert report.reason_codes == ["MEDIA_METADATA_PROBE_REQUIRED"]


def test_cvl_predicts_safe_to_use_false_before_truth_readiness() -> None:
    profile = FireTestProfile(
        profile_id="profile_media_inventory_safe_false",
        name="Media inventory safe to use false",
        objective="Predict unsafe inventory before truth readiness.",
        domain="generic",
        expected_pipeline=[
            "media_inventory_sufficiency",
            "truth_readiness",
        ],
        involved_contracts=["media_corpus_inventory_contract"],
        expected_capabilities=["media_metadata_reader"],
        metadata={
            "inventory_sufficiency": {
                "status": "satisfied",
                "coverage_status": "satisfied",
                "safe_to_use": False,
                "confidence": 0.9,
            },
            "metadata_coverage": {
                "status": "satisfied",
                "files_expected": 8,
                "files_succeeded": 8,
            },
        },
    )
    graph = CognitiveDependencyGraphService().build(profile)

    report = CognitiveGapPredictor().predict(
        profile,
        graph=graph,
        available_capabilities=["media_metadata_reader"],
    )

    assert report.predicted_status == "blocked"
    assert report.probable_component == "media_inventory_sufficiency"
    assert report.reason_codes == ["MEDIA_INVENTORY_SAFE_TO_USE_FALSE"]
