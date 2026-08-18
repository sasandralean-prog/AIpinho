from __future__ import annotations

from aipinho.schemas.cvl import FireTestProfile
from aipinho.services.cvl import CognitiveGapPredictor


def test_cvl_predicts_partial_artifact_acceptance_frontier() -> None:
    profile = FireTestProfile(
        profile_id="profile_phase1_partial_policy",
        name="Phase 1 partial policy",
        objective="Predict phase completion policy before runtime execution.",
        expected_pipeline=["semantic_completion", "completion", "speaker_truth"],
        involved_contracts=["phase_semantic_completion_policy", "media_corpus_inventory_artifact"],
        expected_capabilities=[],
        expected_artifacts=["reports/example/media_inventory.csv"],
        success_contract={"speaker_truth": "safe"},
        metadata={
            "phase_semantic_completion_policy": {
                "partial_artifact_acceptance": "required",
                "confidence": 0.87,
            }
        },
    )

    report = CognitiveGapPredictor().predict(profile, available_capabilities=[])

    assert report.predicted_status == "blocked"
    assert report.probable_component == "phase_semantic_completion_policy"
    assert report.reason_codes == ["PARTIAL_ARTIFACT_ACCEPTANCE_REQUIRED"]
    assert report.confidence == 0.87
