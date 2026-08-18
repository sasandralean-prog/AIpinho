from __future__ import annotations

from aipinho.schemas.artifacts.relationship import RelationshipGoal, RelationshipValidationPolicy
from aipinho.schemas.cvl import FireTestProfile
from aipinho.services.artifacts.artifact_semantic_contract_service import ArtifactSemanticContractService
from aipinho.services.artifacts.media_relationship_candidate_service import MediaRelationshipCandidateService
from aipinho.services.artifacts.relationship_validation_policy_service import RelationshipValidationPolicyService
from aipinho.services.cvl import CognitiveDependencyGraphService, CognitiveGapPredictor
from aipinho.services.runtime.universal_task_session_service import UniversalTaskSessionService

from tests.unit.test_media_relationship_foundation import _entity


def _detection(*entities: dict) -> dict:
    return MediaRelationshipCandidateService().detect(
        entities=list(entities),
        relationship_goal=RelationshipGoal(allowed_relation_families=["textual_sidecar_candidate"]),
        artifact_contract={"contract_id": "generic_relationship_contract", "expected_relationships": [{}]},
    )


def _observation_payload(detection: dict, index: int = 0) -> dict:
    candidate = detection["candidates"][index]
    observation = detection["observations"][index]
    return {
        "observation_id": observation.observation_id,
        "candidate_id": candidate.candidate_id,
        "source_entity_id": candidate.source_entity_id,
        "target_entity_id": candidate.target_entity_id,
        "relation_family": candidate.relation_family,
        "relation_kind_candidate": candidate.relation_kind_candidate,
        "evidence_refs": candidate.evidence_refs,
        "confidence": candidate.confidence,
        "confidence_model": candidate.confidence_model.model_dump(mode="json"),
        "provenance_trace_id": candidate.provenance_trace_id,
        "negative_evidence": [item.model_dump(mode="json") for item in candidate.negative_evidence],
        "conflicts": [item.model_dump(mode="json") for item in candidate.conflicts],
        "truth_eligible": False,
        "validation_required": True,
    }


def _record_payload(detection: dict, index: int = 0) -> dict:
    return detection["evidence_records"][index].model_dump(mode="json")


def test_candidate_with_isolated_signal_is_not_validation_ready() -> None:
    result = RelationshipValidationPolicyService().validate_many(
        relationship_observations=[
            {
                "candidate_id": "candidate_isolated_signal",
                "source_entity_id": "source",
                "target_entity_id": "target",
                "evidence_refs": ["relationship_evidence_1"],
                "confidence": 0.9,
                "confidence_model": {
                    "normalized_score": 0.9,
                    "signal_contributions": [{"signal_type": "normalized_stem_similarity"}],
                },
                "provenance_trace_id": "trace_1",
            }
        ],
        provenance_traces=[{"trace_id": "trace_1"}],
        evidence_records=[
            {
                "evidence_id": "relationship_evidence_1",
                "evidence_type": "relationship_observation",
                "candidate_id": "candidate_isolated_signal",
            }
        ],
    )

    assert result[0].status == "not_ready"
    assert "RELATIONSHIP_SIGNAL_DIVERSITY_INSUFFICIENT" in result[0].reason_codes
    assert result[0].truth_eligible is False
    assert result[0].speaker_claim_allowed is False


def test_candidate_with_missing_provenance_is_not_validation_ready() -> None:
    detection = _detection(
        _entity("track", "album/song.media", role="media_asset_candidate"),
        _entity("text", "album/song.text", role="text_sidecar_candidate"),
    )
    observation = _observation_payload(detection)
    observation["provenance_trace_id"] = None

    result = RelationshipValidationPolicyService().validate_many(
        relationship_observations=[observation],
        provenance_traces=[],
        evidence_records=[_record_payload(detection)],
    )

    assert result[0].status == "not_ready"
    assert "RELATIONSHIP_PROVENANCE_MISSING" in result[0].reason_codes
    assert result[0].missing_requirements == ["provenance_trace_id"]


def test_candidate_with_blocking_conflict_is_conflicted() -> None:
    detection = _detection(
        _entity("track", "album/song.media", role="media_asset_candidate"),
        _entity("text", "album/song.text", role="text_sidecar_candidate", root_role="external_root"),
    )

    result = RelationshipValidationPolicyService().validate_many(
        relationship_observations=[_observation_payload(detection)],
        provenance_traces=[item.model_dump(mode="json") for item in detection["provenance_traces"]],
        evidence_records=[_record_payload(detection)],
    )

    assert result[0].status == "conflicted"
    assert "RELATIONSHIP_CONFLICT_BLOCKED" in result[0].reason_codes
    assert result[0].truth_eligible is False


def test_ambiguous_candidate_is_blocked_until_disambiguated() -> None:
    detection = _detection(
        _entity("track", "album/song.media", role="media_asset_candidate"),
        _entity("text_a", "album/song.text", role="text_sidecar_candidate"),
        _entity("text_b", "album/song.notes", role="text_sidecar_candidate"),
    )
    observations = [_observation_payload(detection, index) for index, _ in enumerate(detection["candidates"])]

    result = RelationshipValidationPolicyService().validate_many(
        relationship_observations=observations,
        provenance_traces=[item.model_dump(mode="json") for item in detection["provenance_traces"]],
        evidence_records=[item.model_dump(mode="json") for item in detection["evidence_records"]],
    )

    assert any(item.status == "blocked" for item in result)
    assert any("RELATIONSHIP_AMBIGUITY_UNRESOLVED" in item.reason_codes for item in result)


def test_sufficient_evidence_becomes_validation_ready_but_not_truth() -> None:
    detection = _detection(
        _entity("track", "album/song.media", role="media_asset_candidate"),
        _entity("text", "album/song.text", role="text_sidecar_candidate"),
    )

    result = RelationshipValidationPolicyService().validate_many(
        relationship_observations=[_observation_payload(detection)],
        provenance_traces=[item.model_dump(mode="json") for item in detection["provenance_traces"]],
        evidence_records=[_record_payload(detection)],
    )

    assert result[0].status == "validation_ready"
    assert "RELATIONSHIP_VALIDATION_READY" in result[0].reason_codes
    assert result[0].truth_eligible is False
    assert result[0].speaker_claim_allowed is False


def test_validated_policy_status_still_does_not_allow_speaker_truth() -> None:
    detection = _detection(
        _entity("track", "album/song.media", role="media_asset_candidate"),
        _entity("text", "album/song.text", role="text_sidecar_candidate"),
    )

    result = RelationshipValidationPolicyService().validate_many(
        relationship_observations=[_observation_payload(detection)],
        provenance_traces=[item.model_dump(mode="json") for item in detection["provenance_traces"]],
        evidence_records=[_record_payload(detection)],
        policy=RelationshipValidationPolicy(allow_validated_status=True),
    )

    assert result[0].status == "validated"
    assert result[0].truth_eligible is False
    assert result[0].speaker_claim_allowed is False


def test_artifact_profile_receives_relationship_validation_summary() -> None:
    detection = _detection(
        _entity("track", "album/song.media", role="media_asset_candidate"),
        _entity("text", "album/song.text", role="text_sidecar_candidate"),
    )

    validation = ArtifactSemanticContractService().validate(
        logical_path="reports/entities.csv",
        content_type="text/csv",
        content="name\nsong\n",
        declared_contract={
            "expected_kind": "tabular_collection",
            "expected_schema": ["name"],
            "expected_relationships": [{"family": "textual_sidecar_candidate"}],
            "relationship_fields": [
                "relationship_validation_status",
                "relationship_validation_reason_codes",
                "relationship_validation_ready_count",
                "relationship_conflicted_count",
            ],
            "artifact_relationship_binding": {
                "status": "bound",
                "bound_relationship_observations": [_observation_payload(detection)],
                "relationship_provenance_traces": [
                    item.model_dump(mode="json") for item in detection["provenance_traces"]
                ],
                "relationship_evidence_records": [
                    item.model_dump(mode="json") for item in detection["evidence_records"]
                ],
            },
        },
    )

    assert validation.status == "blocked"
    assert validation.profile is not None
    assert validation.profile.validation_ready_count == 1
    assert validation.profile.validated_relationship_count == 0
    assert validation.profile.truth_eligible_relationship_count == 0
    assert validation.profile.relationship_validation_results[0]["status"] == "validation_ready"
    assert validation.profile.relationship_rendered_fields["relationship_validation_status"] == "validation_ready"
    assert "relationship_final_validation_missing" in validation.missing_requirements


def test_relationship_summary_reports_readiness_counts_lightly() -> None:
    summary = UniversalTaskSessionService()._relationship_cognition_summary(
        [{"candidate_count": 1, "observation_count": 1, "evidence_count": 3}],
        [],
        [
            {
                "rendered_field_count": 4,
                "validation_status": "validation_ready",
                "validation_ready_count": 1,
                "validated_relationship_count": 0,
                "conflicted_relationship_count": 0,
            }
        ],
    )

    assert summary["validation_status"] == "validation_ready"
    assert summary["validation_ready_count"] == 1
    assert summary["validated_relationship_count"] == 0
    assert summary["truth_eligible"] is False


def test_cvl_recognizes_relationship_validation_policy_frontier() -> None:
    profile = FireTestProfile(
        profile_id="profile_relationship_validation_policy",
        name="Relationship validation policy",
        objective="Predict validation policy readiness without runtime execution.",
        domain="generic",
        expected_pipeline=["relationship_evidence", "relationship_validation", "speaker_truth"],
        involved_contracts=["relationship_candidate_contract"],
        expected_capabilities=["media_relationship_candidate_detector"],
        metadata={
            "relationship_cognition": {
                "capability_id": "media_relationship_candidate_detector",
                "capability_status": "registered",
                "evidence_status": "sufficient",
                "provenance_status": "complete",
                "validation_policy_status": "missing",
                "confidence": 0.83,
            }
        },
    )
    graph = CognitiveDependencyGraphService().build(profile)

    report = CognitiveGapPredictor().predict(
        profile,
        graph=graph,
        available_capabilities=["media_relationship_candidate_detector"],
    )

    assert report.probable_component == "relationship_validation_policy"
    assert report.reason_codes == ["RELATIONSHIP_VALIDATION_POLICY_MISSING"]
    assert report.confidence == 0.83
