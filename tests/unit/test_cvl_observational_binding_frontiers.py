from aipinho.schemas.cvl import FireTestProfile
from aipinho.services.cvl import CognitiveDependencyGraphService, CognitiveGapPredictor


def test_cvl_predicts_observational_binding_frontier_from_profile_metadata() -> None:
    profile = FireTestProfile(
        profile_id="profile_observational_binding",
        name="Observational binding frontier",
        objective="Predict whether semantic artifact rows have governed evidence bindings.",
        domain="semantic_artifacts",
        expected_pipeline=[
            "intent",
            "artifact_semantic_contract",
            "observational_binding",
            "artifact_evidence_binding",
            "validation",
        ],
        involved_contracts=["media_corpus_inventory_artifact"],
        expected_capabilities=["artifact_observation_binding"],
        metadata={
            "observational_binding": {
                "observational_binding_status": "insufficient",
                "confidence": 0.87,
            }
        },
    )
    graph = CognitiveDependencyGraphService().build(profile)

    report = CognitiveGapPredictor().predict(profile, graph=graph, available_capabilities=["artifact_observation_binding"])

    assert report.predicted_status == "blocked"
    assert report.probable_component == "observational_binding"
    assert report.reason_codes == ["OBSERVATIONAL_BINDING_INSUFFICIENT"]
    assert report.confidence == 0.87


def test_cvl_predicts_artifact_evidence_binding_frontier_from_profile_metadata() -> None:
    profile = FireTestProfile(
        profile_id="profile_artifact_evidence_binding",
        name="Artifact evidence binding frontier",
        objective="Predict whether semantic artifacts have row evidence refs.",
        domain="semantic_artifacts",
        expected_pipeline=[
            "intent",
            "artifact_semantic_contract",
            "artifact_evidence_binding",
            "validation",
        ],
        involved_contracts=["media_corpus_inventory_artifact"],
        expected_capabilities=["artifact_observation_binding"],
        metadata={
            "artifact_evidence_binding": {
                "status": "missing",
                "confidence": 0.79,
            }
        },
    )
    graph = CognitiveDependencyGraphService().build(profile)

    report = CognitiveGapPredictor().predict(profile, graph=graph, available_capabilities=["artifact_observation_binding"])

    assert report.predicted_status == "blocked"
    assert report.probable_component == "artifact_evidence_binding"
    assert report.reason_codes == ["ARTIFACT_EVIDENCE_BINDING_MISSING"]
    assert report.confidence == 0.79


def test_cvl_predicts_corpus_root_policy_frontier_from_profile_metadata() -> None:
    profile = FireTestProfile(
        profile_id="profile_corpus_policy",
        name="Corpus root policy frontier",
        objective="Predict whether declared corpus roots can be observed.",
        domain="semantic_artifacts",
        expected_pipeline=[
            "intent",
            "root_binding",
            "observed_entity_compilation",
            "artifact_evidence_binding",
        ],
        involved_contracts=["media_corpus_inventory_artifact"],
        metadata={
            "observational_binding": {
                "root_policy_status": "blocked",
                "confidence": 0.81,
            }
        },
    )
    graph = CognitiveDependencyGraphService().build(profile)

    report = CognitiveGapPredictor().predict(profile, graph=graph, available_capabilities=["artifact_observation_binding"])

    assert report.predicted_status == "blocked"
    assert report.probable_component == "root_binding"
    assert report.reason_codes == ["CORPUS_ROOT_POLICY_BLOCKED"]


def test_cvl_predicts_observed_entity_role_projection_frontier_from_profile_metadata() -> None:
    profile = FireTestProfile(
        profile_id="profile_role_projection",
        name="Observed entity role projection frontier",
        objective="Predict whether corpus roots project into observed entities.",
        domain="semantic_artifacts",
        expected_pipeline=[
            "intent",
            "root_binding",
            "observed_entity_compilation",
            "semantic_entity_selection",
        ],
        involved_contracts=["media_corpus_inventory_artifact"],
        metadata={
            "observational_binding": {
                "root_role_projection_status": "missing",
                "confidence": 0.82,
            }
        },
    )
    graph = CognitiveDependencyGraphService().build(profile)

    report = CognitiveGapPredictor().predict(profile, graph=graph, available_capabilities=["artifact_observation_binding"])

    assert report.predicted_status == "blocked"
    assert report.probable_component == "observed_entity_compilation"
    assert report.reason_codes == ["OBSERVED_ENTITY_ROLE_PROJECTION_MISSING"]
