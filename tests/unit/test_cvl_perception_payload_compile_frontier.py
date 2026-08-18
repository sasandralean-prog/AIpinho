from aipinho.schemas.cvl import FireTestProfile
from aipinho.services.cvl.cognitive_validation_laboratory_service import (
    CognitiveDependencyGraphService,
    CognitiveGapPredictor,
)


def test_cvl_predicts_generic_perception_payload_compile_frontier_without_runtime() -> None:
    profile = FireTestProfile(
        profile_id="generic_perception_compile_boundary",
        name="Generic perception compile boundary",
        domain="runtime_perception",
        objective="Predict a bounded perception payload compile frontier without executing runtime.",
        expected_pipeline=["selected_entities", "contract_driven_perception_compile", "artifact_runtime"],
        involved_contracts=["contract_driven_perception"],
        expected_capabilities=[],
        expected_artifacts=[],
        success_contract={},
        metadata={
            "public_response_boundary": {
                "perception_compile_boundary": "entity_projection",
            }
        },
    )
    graph = CognitiveDependencyGraphService().build(profile)

    prediction = CognitiveGapPredictor().predict(profile, graph=graph)

    assert prediction.predicted_status == "blocked"
    assert prediction.probable_component == "ContractDrivenPerceptionService"
    assert prediction.reason_codes == ["PERCEPTION_PAYLOAD_COMPILE_BOUNDARY"]
    assert "runtime" not in prediction.evidence_refs
