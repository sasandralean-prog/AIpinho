from aipinho.schemas.cvl import FireTestProfile
from aipinho.services.cvl.cognitive_validation_laboratory_service import (
    CognitiveDependencyGraphService,
    CognitiveGapPredictor,
)


def test_cvl_predicts_fact_source_binding_frontier_without_runtime() -> None:
    profile = FireTestProfile(
        profile_id="generic_source_binding_boundary",
        name="Generic source binding boundary",
        domain="runtime_perception",
        objective="Predict source binding frontier without executing runtime.",
        expected_pipeline=["selected_entities", "contract_driven_perception_compile", "fact_source_binding"],
        involved_contracts=["contract_driven_perception"],
        expected_capabilities=[],
        expected_artifacts=[],
        success_contract={},
        metadata={
            "public_response_boundary": {
                "fact_source_binding": "evidence_set_materialization",
            }
        },
    )
    graph = CognitiveDependencyGraphService().build(profile)

    prediction = CognitiveGapPredictor().predict(profile, graph=graph)

    assert prediction.predicted_status == "blocked"
    assert prediction.probable_component == "ContractDrivenPerceptionService"
    assert prediction.reason_codes == ["PERCEPTION_FACT_SOURCE_BINDING_FRONTIER"]
    assert "runtime" not in prediction.evidence_refs
