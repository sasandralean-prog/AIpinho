from __future__ import annotations

from aipinho.schemas.artifacts.relationship import RelationshipGoal
from aipinho.services.artifacts.artifact_semantic_contract_service import ArtifactSemanticContractService
from aipinho.services.artifacts.media_relationship_candidate_service import MediaRelationshipCandidateService

from tests.unit.test_media_relationship_foundation import _entity


def test_relationship_signals_include_provenance_and_are_never_sufficient_alone() -> None:
    result = MediaRelationshipCandidateService().detect(
        entities=[
            _entity("track", "album/song.media", role="media_asset_candidate"),
            _entity("text", "album/song.text", role="text_sidecar_candidate"),
        ],
        relationship_goal=RelationshipGoal(allowed_relation_families=["textual_sidecar_candidate"]),
        artifact_contract={"contract_id": "generic_relationship_contract", "expected_relationships": [{}]},
    )

    assert result["candidates"]
    for signal in result["provenance_traces"][0].signals_used:
        assert signal["signal_id"]
        assert signal["source_entity_ref"]["entity_id"]
        assert signal["target_entity_ref"]["entity_id"]
        assert signal["confidence_weight"] == 1.0
        assert signal["confidence_method"] == "weighted_signal_contribution"
        assert signal["is_sufficient_alone"] is False


def test_candidate_includes_provenance_trace_and_confidence_model() -> None:
    result = MediaRelationshipCandidateService().detect(
        entities=[
            _entity("track", "album/song.media", role="media_asset_candidate"),
            _entity("text", "album/song.text", role="text_sidecar_candidate"),
        ],
        relationship_goal=RelationshipGoal(allowed_relation_families=["textual_sidecar_candidate"]),
        artifact_contract={"contract_id": "generic_relationship_contract", "expected_relationships": [{}]},
    )

    candidate = result["candidates"][0]
    record = result["evidence_records"][0]
    trace = result["provenance_traces"][0]

    assert candidate.provenance_trace_id == trace.trace_id
    assert candidate.confidence_model is not None
    assert candidate.confidence_model.positive_signal_count >= 2
    assert "high_confidence_is_not_truth" in candidate.confidence_model.calibration_notes
    assert record.provenance_trace_id == trace.trace_id
    assert record.observation_id == result["observations"][0].observation_id
    assert record.validation_required is True
    assert record.truth_eligible is False


def test_negative_evidence_reduces_confidence_without_rejecting_candidate_truthfully() -> None:
    baseline = MediaRelationshipCandidateService().detect(
        entities=[
            _entity("track", "album/song.media", role="media_asset_candidate"),
            _entity("text", "album/song.text", role="text_sidecar_candidate"),
        ],
        relationship_goal=RelationshipGoal(allowed_relation_families=["textual_sidecar_candidate"]),
        artifact_contract={"expected_relationships": [{}]},
    )
    penalized = MediaRelationshipCandidateService().detect(
        entities=[
            _entity("track", "album/song.media", role="media_asset_candidate"),
            _entity("text", "album/song.text", role="text_sidecar_candidate", root_role="external_root"),
        ],
        relationship_goal=RelationshipGoal(allowed_relation_families=["textual_sidecar_candidate"]),
        artifact_contract={"expected_relationships": [{}]},
    )

    assert penalized["candidates"]
    assert penalized["candidates"][0].confidence < baseline["candidates"][0].confidence
    assert penalized["candidates"][0].negative_evidence
    assert penalized["candidates"][0].truth_eligible is False


def test_conflict_is_preserved_and_blocks_future_validation_readiness() -> None:
    result = MediaRelationshipCandidateService().detect(
        entities=[
            _entity("track", "album/song.media", role="media_asset_candidate"),
            _entity("text", "album/song.text", role="text_sidecar_candidate", root_role="external_root"),
        ],
        relationship_goal=RelationshipGoal(allowed_relation_families=["textual_sidecar_candidate"]),
        artifact_contract={"expected_relationships": [{}]},
    )

    candidate = result["candidates"][0]
    assert candidate.conflicts
    assert candidate.confidence_model is not None
    assert candidate.confidence_model.conflict_count == 1
    assert candidate.confidence_model.confidence_band == "conflicted"
    assert candidate.reason_codes[-1] == "RELATIONSHIP_CONFLICT_PRESENT"
    assert candidate.conflicts[0].blocks_validation_ready is True


def test_artifact_profile_preserves_relationship_provenance_conflict_and_negative_evidence() -> None:
    result = MediaRelationshipCandidateService().detect(
        entities=[
            _entity("track", "album/song.media", role="media_asset_candidate"),
            _entity("text", "album/song.text", role="text_sidecar_candidate", root_role="external_root"),
        ],
        relationship_goal=RelationshipGoal(allowed_relation_families=["textual_sidecar_candidate"]),
        artifact_contract={"expected_relationships": [{}]},
    )
    candidate = result["candidates"][0]
    observation = result["observations"][0]

    validation = ArtifactSemanticContractService().validate(
        logical_path="reports/entities.csv",
        content_type="text/csv",
        content="name\nsong\n",
        declared_contract={
            "expected_kind": "tabular_collection",
            "expected_schema": ["name"],
            "expected_relationships": [{"family": "textual_sidecar_candidate"}],
            "artifact_relationship_binding": {
                "status": "bound",
                "bound_relationship_observations": [
                    {
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
                ],
                "relationship_provenance_traces": [
                    item.model_dump(mode="json") for item in result["provenance_traces"]
                ],
            },
        },
    )

    assert validation.status == "blocked"
    assert "relationship_conflict_present" in validation.missing_requirements
    assert "relationship_final_validation_missing" in validation.missing_requirements
    profile = validation.profile
    assert profile is not None
    assert profile.relationship_provenance_traces
    assert profile.relationship_binding_quality["status"] == "complete"
    assert profile.relationship_conflict_summary["blocking_conflict_count"] == 1
    assert profile.relationship_negative_evidence_summary["negative_evidence_count"] >= 1
