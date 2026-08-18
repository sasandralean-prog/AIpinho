from aipinho.schemas.cvl import FireTestProfile
from aipinho.services.cvl.cognitive_validation_laboratory_service import (
    CognitiveDependencyGraphService,
    CognitiveGapPredictor,
)


def test_cvl_predicts_perception_fact_projection_frontier_without_runtime() -> None:
    profile = FireTestProfile(
        profile_id="generic_fact_projection_boundary",
        name="Generic fact projection boundary",
        domain="runtime_perception",
        objective="Predict a fact projection frontier without executing runtime.",
        expected_pipeline=["selected_entities", "contract_driven_perception_compile", "fact_projection"],
        involved_contracts=["contract_driven_perception"],
        expected_capabilities=[],
        expected_artifacts=[],
        success_contract={},
        metadata={
            "public_response_boundary": {
                "perception_fact_projection": "provenance_binding",
            }
        },
    )
    graph = CognitiveDependencyGraphService().build(profile)

    prediction = CognitiveGapPredictor().predict(profile, graph=graph)

    assert prediction.predicted_status == "blocked"
    assert prediction.probable_component == "ContractDrivenPerceptionService"
    assert prediction.reason_codes == ["PERCEPTION_FACT_PROJECTION_FRONTIER"]
    assert "runtime" not in prediction.evidence_refs
