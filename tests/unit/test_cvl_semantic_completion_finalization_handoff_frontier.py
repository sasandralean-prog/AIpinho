from __future__ import annotations

from aipinho.schemas.cvl import FireTestProfile
from aipinho.services.cvl import CognitiveGapPredictor


def test_cvl_predicts_semantic_completion_finalization_handoff_frontier() -> None:
    profile = FireTestProfile(
        profile_id="profile_semantic_handoff",
        name="Semantic handoff",
        objective="Predict semantic finalization handoff before runtime repair.",
        expected_pipeline=["artifact_runtime", "semantic_completion", "result_persistence"],
        involved_contracts=["phase_semantic_completion_policy", "terminal_result_contract"],
        expected_capabilities=[],
        expected_artifacts=["reports/example/media_inventory.csv"],
        success_contract={"speaker_truth": "safe"},
        metadata={
            "phase_semantic_completion_policy": {
                "semantic_finalization_handoff": "missing",
                "confidence": 0.91,
                "capability_id": "semantic_completion_finalization_handoff",
            }
        },
    )

    report = CognitiveGapPredictor().predict(profile, available_capabilities=[])

    assert report.predicted_status == "blocked"
    assert report.probable_component == "semantic_completion_finalization_handoff"
    assert report.probable_capability == "semantic_completion_finalization_handoff"
    assert report.reason_codes == ["SEMANTIC_COMPLETION_FINALIZATION_HANDOFF_MISSING"]
