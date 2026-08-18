from __future__ import annotations

from aipinho.schemas.cvl import FireTestProfile
from aipinho.services.cvl import CognitiveValidationLaboratoryService


def test_cvl_predicts_music_inventory_post_selection_frontier_without_runtime() -> None:
    profile = FireTestProfile(
        profile_id="profile_music_inventory_post_selection_stall",
        name="Music inventory post-selection stall frontier",
        objective="Predict post-selection render/perception stall without executing runtime.",
        expected_pipeline=["public runtime boundary", "media corpus inventory artifact"],
        involved_contracts=["media_corpus_inventory_artifact"],
        metadata={
            "public_response_boundary": {
                "music_inventory_post_selection_stage": "after_entity_selection",
                "confidence": 0.91,
            }
        },
    )

    result = CognitiveValidationLaboratoryService().analyze([profile])
    prediction = result.prediction_reports[0]

    assert prediction.predicted_status == "blocked"
    assert prediction.probable_component == "ReadonlyAnalysisArtifactRuntimeService"
    assert prediction.reason_codes == ["MUSIC_INVENTORY_POST_SELECTION_RENDER_PERCEPTION_STALL"]
    assert prediction.confidence == 0.91
