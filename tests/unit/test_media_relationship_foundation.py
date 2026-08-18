from __future__ import annotations

from aipinho.schemas.artifacts.relationship import RelationshipGoal
from aipinho.services.artifacts.artifact_semantic_contract_service import ArtifactSemanticContractService
from aipinho.services.artifacts.contract_driven_perception_service import CapabilityRegistry, ContractDrivenPerceptionService
from aipinho.services.artifacts.media_relationship_candidate_service import MediaRelationshipCandidateService
from aipinho.services.runtime.universal_task_session_service import UniversalTaskSessionService


def _entity(entity_id: str, source: str, *, role: str = "media_asset_candidate", root_role: str = "library_root") -> dict:
    name = source.rsplit("/", 1)[-1]
    return {
        "entity_id": entity_id,
        "entity_kind": "file",
        "name": name,
        "source": source,
        "relative_path": source,
        "source_root_role": root_role,
        "entity_role": role,
        "confidence": 1.0,
        "observed_attributes": {
            "name": {"name": "name", "value": name, "status": "observed", "confidence": 1.0, "evidence_refs": []},
            "relative_path": {"name": "relative_path", "value": source, "status": "observed", "confidence": 1.0, "evidence_refs": []},
            "source_root_role": {"name": "source_root_role", "value": root_role, "status": "observed", "confidence": 1.0, "evidence_refs": []},
            "entity_role": {"name": "entity_role", "value": role, "status": "observed", "confidence": 1.0, "evidence_refs": []},
        },
        "evidence_refs": [],
    }


def _graph(*entities: dict) -> dict:
    return {
        "entity_set_id": "entity_graph_relationship_test",
        "roots_scanned_by_role": {"library_root": ["library"]},
        "entities_by_root_role": {"library_root": len(entities)},
        "entities": list(entities),
    }


def test_relationship_candidate_starts_without_truth_eligibility() -> None:
    service = MediaRelationshipCandidateService()
    goal = RelationshipGoal(
        allowed_relation_families=["textual_sidecar_candidate"],
        required_evidence_types=["relationship_observation"],
    )

    result = service.detect(
        entities=[
            _entity("track", "album/song_one.media", role="media_asset_candidate"),
            _entity("text", "album/song_one.text", role="text_sidecar_candidate"),
        ],
        relationship_goal=goal,
        artifact_contract={"expected_relationships": [{"family": "textual_sidecar_candidate"}]},
    )

    assert result["candidates"]
    candidate = result["candidates"][0]
    assert candidate.status == "candidate"
    assert candidate.truth_eligible is False
    assert candidate.validation_required is True
    assert result["observations"][0].truth_eligible is False
    assert all(item.is_sufficient_alone is False for item in result["evidence"])
    assert all(item.evidence_type == "relationship_observation" for item in result["evidence_records"])
    assert all(item.truth_eligible is False for item in result["evidence_records"])


def test_single_stem_signal_does_not_create_relationship_candidate() -> None:
    service = MediaRelationshipCandidateService()
    result = service.detect(
        entities=[
            _entity("left", "album_a/shared_name.media", role="", root_role=""),
            _entity("right", "album_b/shared_name.text", role="", root_role=""),
        ],
        relationship_goal=RelationshipGoal(),
    )

    assert result["candidates"] == []
    assert result["reason_codes"] == ["INSUFFICIENT_EVIDENCE_SIGNALS"]


def test_extension_is_not_used_as_relationship_authority() -> None:
    service = MediaRelationshipCandidateService()
    result = service.detect(
        entities=[
            _entity("left", "album/alpha.media", role="media_asset_candidate"),
            _entity("right", "album/beta.text", role="text_sidecar_candidate"),
        ],
        relationship_goal=RelationshipGoal(allowed_relation_families=["textual_sidecar_candidate"]),
        artifact_contract={"expected_relationships": [{"family": "textual_sidecar_candidate"}]},
    )

    signal_types = {item.signal_type for item in result["evidence"]}
    assert "extension" not in signal_types
    assert "file_extension" not in signal_types
    assert all(item.is_sufficient_alone is False for item in result["evidence"])


def test_contract_perception_runs_relationship_detector_only_via_registry() -> None:
    service = ContractDrivenPerceptionService()
    result = service.compile(
        graph=_graph(
            _entity("track", "album/song_one.media", role="media_asset_candidate"),
            _entity("text", "album/song_one.text", role="text_sidecar_candidate"),
        ),
        declared_contract={
            "contract_id": "generic_media_inventory",
            "expected_kind": "tabular_collection",
            "expected_schema": ["name"],
            "expected_relationships": [{"family": "textual_sidecar_candidate"}],
            "relationship_goal": {"allowed_relation_families": ["textual_sidecar_candidate"]},
            "entity_selection_contract": {"allowed_root_roles": ["library_root"]},
        },
    )

    assert result.relationship_goal is not None
    assert result.relationship_candidates
    assert result.relationship_summary["capability_id"] == "media_relationship_candidate_detector"
    assert result.relationship_summary["truth_eligible"] is False
    assert any(item.evidence_type == "relationship_observation" for item in result.evidence_set.records)
    assert result.semantic_self_review.can_speaker_claim is False


def test_relationship_capability_missing_is_reported_without_parallel_registry() -> None:
    registry = CapabilityRegistry(capabilities={"observed_entity_attribute_reader": ["name"]})
    service = ContractDrivenPerceptionService(observer_registry=registry)
    result = service.compile(
        graph=_graph(
            _entity("track", "album/song_one.media", role="media_asset_candidate"),
            _entity("text", "album/song_one.text", role="text_sidecar_candidate"),
        ),
        declared_contract={
            "expected_kind": "tabular_collection",
            "expected_schema": ["name"],
            "expected_relationships": [{"family": "textual_sidecar_candidate"}],
            "entity_selection_contract": {"allowed_root_roles": ["library_root"]},
        },
    )

    assert result.relationship_candidates == []
    assert result.relationship_summary["status"] == "blocked"
    assert result.relationship_summary["reason_codes"] == ["NO_MATCHING_RELATIONSHIP_CAPABILITY"]


def test_artifact_semantic_profile_binds_relationship_observations_without_validation_pass() -> None:
    service = ArtifactSemanticContractService()
    declared = {
        "expected_kind": "tabular_collection",
        "expected_schema": ["name"],
        "expected_relationships": [{"family": "textual_sidecar_candidate"}],
        "artifact_relationship_binding": {
            "status": "bound",
            "bound_relationship_observations": [
                {
                    "observation_id": "relationship_observation_1",
                    "candidate_id": "relationship_candidate_1",
                    "source_entity_id": "track",
                    "target_entity_id": "text",
                    "relation_family": "textual_sidecar_candidate",
                    "relation_kind_candidate": "same_stem_candidate",
                    "evidence_refs": ["relationship_evidence_1"],
                    "capability_id": "media_relationship_candidate_detector",
                    "confidence": 0.71,
                    "truth_eligible": False,
                    "validation_required": True,
                }
            ],
        },
    }

    result = service.validate(
        logical_path="reports/entities.csv",
        content_type="text/csv",
        declared_contract=declared,
        content="name\nsong_one\n",
    )

    assert result.status == "blocked"
    assert "relationship_final_validation_missing" in result.missing_requirements
    assert result.profile is not None
    assert result.profile.bound_relationship_observations[0]["truth_eligible"] is False
    assert result.profile.relationship_evidence_summary["relationship_not_truth_eligible"] is True
    assert result.profile.relationship_confidence_summary["max"] == 0.71


def test_relationship_cognition_summary_is_lightweight_and_not_truth_eligible() -> None:
    service = UniversalTaskSessionService()
    summary = service._relationship_cognition_summary(
        [
            {
                "candidate_count": 2,
                "observation_count": 2,
                "evidence_count": 5,
                "relation_families": ["textual_sidecar_candidate"],
                "confidence_summary": {"max": 0.71},
                "reason_codes": ["RELATIONSHIP_CANDIDATE_OBSERVED"],
            }
        ],
        [],
    )

    assert summary == {
        "status": "available",
        "candidate_count": 2,
        "observation_count": 2,
        "evidence_count": 5,
        "provenance_trace_count": 0,
        "conflict_count": 0,
        "negative_evidence_count": 0,
        "rendered_field_count": 0,
        "evidence_ref_count": 0,
        "provenance_ref_count": 0,
        "validation_ready_count": 0,
        "validated_relationship_count": 0,
        "conflicted_relationship_count": 0,
        "relation_families": ["textual_sidecar_candidate"],
        "confidence_summary": {"count": 1, "max": 0.71, "average": 0.71},
        "truth_eligible": False,
        "validation_status": "validation_required",
        "reason_codes": ["RELATIONSHIP_CANDIDATE_OBSERVED"],
        "source": "artifact_relationship_binding",
    }
