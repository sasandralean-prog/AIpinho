from __future__ import annotations

from aipinho.schemas.artifacts.relationship import RelationshipValidationPolicy
from aipinho.services.artifacts.artifact_semantic_contract_service import ArtifactSemanticContractService
from aipinho.services.artifacts.contract_driven_perception_service import CapabilityRegistry, ContractDrivenPerceptionService
from aipinho.services.artifacts.media_relationship_candidate_service import MediaRelationshipCandidateService
from aipinho.services.artifacts.relationship_validation_policy_service import RelationshipValidationPolicyService
from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import ReadonlyAnalysisArtifactRuntimeService
from aipinho.services.runtime.universal_task_session_service import UniversalTaskSessionService

from tests.unit.test_media_relationship_foundation import _entity, _graph


def _relationship_contract() -> dict:
    return {
        "contract_id": "generic_relationship_stack_contract",
        "expected_kind": "tabular_collection",
        "expected_schema": ["name"],
        "expected_relationships": [{"family": "textual_sidecar_candidate"}],
        "relationship_goal": {"allowed_relation_families": ["textual_sidecar_candidate"]},
        "relationship_fields": [
            "relationship_candidate_count",
            "relationship_top_family",
            "relationship_validation_status",
            "relationship_validation_reason_codes",
            "relationship_validation_ready_count",
            "relationship_conflicted_count",
            "relationship_evidence_ref_count",
            "relationship_provenance_ref_count",
        ],
        "entity_selection_contract": {"allowed_root_roles": ["library_root", "external_root"]},
    }


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
        "limitations": list(candidate.limitations),
        "truth_eligible": False,
        "validation_required": True,
    }


def test_relationship_stack_end_to_end_candidate_reaches_validation_ready_without_truth() -> None:
    perception = ContractDrivenPerceptionService().compile(
        graph=_graph(
            _entity("track", "collection/song.media", role="media_asset_candidate"),
            _entity("text", "collection/song.text", role="text_sidecar_candidate"),
        ),
        declared_contract=_relationship_contract(),
    )

    assert perception.relationship_goal is not None
    assert perception.relationship_candidates
    assert perception.relationship_evidence
    assert perception.relationship_provenance_traces
    assert any(item.evidence_type == "relationship_observation" for item in perception.evidence_set.records)
    assert perception.semantic_self_review.can_speaker_claim is False

    validation = ArtifactSemanticContractService().validate(
        logical_path="reports/relationship_stack.csv",
        content_type="text/csv",
        content="name\nsong\n",
        declared_contract={
            **_relationship_contract(),
            "perception": perception.model_dump(mode="json"),
        },
    )

    profile = validation.profile
    assert validation.status == "blocked"
    assert profile is not None
    assert profile.bound_relationship_observations
    assert profile.relationship_provenance_traces
    assert profile.relationship_validation_results
    assert profile.relationship_validation_results[0]["status"] == "validation_ready"
    assert profile.validation_ready_count >= 1
    assert profile.truth_eligible_relationship_count == 0
    assert profile.relationship_rendered_fields["relationship_validation_status"] == "validation_ready"
    assert profile.relationship_rendered_fields["relationship_validation_ready_count"] >= 1
    assert "relationship_final_validation_missing" in validation.missing_requirements

    summary = UniversalTaskSessionService()._relationship_cognition_summary(
        [perception.relationship_summary],
        [
            {
                "bound_relationship_observation_count": len(profile.bound_relationship_observations),
                "candidate_count": len(perception.relationship_candidates),
                "evidence_signal_count": len(perception.relationship_evidence),
                "relationship_provenance_traces": profile.relationship_provenance_traces,
                "relation_families": profile.relationship_rendered_fields.get("relationship_candidate_families", []),
            }
        ],
        [profile.relationship_rendering_summary],
    )

    assert summary["status"] == "available"
    assert summary["candidate_count"] >= 1
    assert summary["validation_status"] == "validation_ready"
    assert summary["validation_ready_count"] >= 1
    assert summary["truth_eligible"] is False
    assert "bound_relationship_observations" not in summary
    assert "relationship_provenance_traces" not in summary


def test_relationship_stack_blocks_isolated_signal_before_readiness() -> None:
    result = RelationshipValidationPolicyService().validate_many(
        relationship_observations=[
            {
                "candidate_id": "candidate_isolated_signal",
                "source_entity_id": "source",
                "target_entity_id": "target",
                "evidence_refs": ["evidence_isolated"],
                "confidence": 0.9,
                "confidence_model": {
                    "normalized_score": 0.9,
                    "signal_contributions": [{"signal_type": "normalized_stem_similarity"}],
                },
                "provenance_trace_id": "trace_isolated",
            }
        ],
        provenance_traces=[{"trace_id": "trace_isolated"}],
        evidence_records=[
            {
                "evidence_id": "evidence_isolated",
                "evidence_type": "relationship_observation",
                "candidate_id": "candidate_isolated_signal",
            }
        ],
    )

    assert result[0].status == "not_ready"
    assert "RELATIONSHIP_SIGNAL_DIVERSITY_INSUFFICIENT" in result[0].reason_codes
    assert result[0].truth_eligible is False


def test_relationship_stack_conflict_stays_conflicted_and_not_truth() -> None:
    detection = MediaRelationshipCandidateService().detect(
        entities=[
            _entity("track", "collection/song.media", role="media_asset_candidate"),
            _entity("text", "collection/song.text", role="text_sidecar_candidate", root_role="external_root"),
        ],
        relationship_goal=ContractDrivenPerceptionService().relationship_goal(
            plan=ContractDrivenPerceptionService().contract_observation_plan(_relationship_contract()),
            declared_contract=_relationship_contract(),
        ),
        artifact_contract=_relationship_contract(),
    )

    results = RelationshipValidationPolicyService().validate_many(
        relationship_observations=[_observation_payload(detection)],
        provenance_traces=[item.model_dump(mode="json") for item in detection["provenance_traces"]],
        evidence_records=[item.model_dump(mode="json") for item in detection["evidence_records"]],
    )

    assert results[0].status == "conflicted"
    assert "RELATIONSHIP_CONFLICT_BLOCKED" in results[0].reason_codes
    assert results[0].speaker_claim_allowed is False


def test_relationship_stack_ambiguity_blocks_readiness() -> None:
    detection = MediaRelationshipCandidateService().detect(
        entities=[
            _entity("track", "collection/song.media", role="media_asset_candidate"),
            _entity("text_a", "collection/song.text", role="text_sidecar_candidate"),
            _entity("text_b", "collection/song.notes", role="text_sidecar_candidate"),
        ],
        relationship_goal=ContractDrivenPerceptionService().relationship_goal(
            plan=ContractDrivenPerceptionService().contract_observation_plan(_relationship_contract()),
            declared_contract=_relationship_contract(),
        ),
        artifact_contract=_relationship_contract(),
    )

    results = RelationshipValidationPolicyService().validate_many(
        relationship_observations=[_observation_payload(detection, index) for index, _ in enumerate(detection["candidates"])],
        provenance_traces=[item.model_dump(mode="json") for item in detection["provenance_traces"]],
        evidence_records=[item.model_dump(mode="json") for item in detection["evidence_records"]],
    )

    assert any(item.status == "blocked" for item in results)
    assert any("RELATIONSHIP_AMBIGUITY_UNRESOLVED" in item.reason_codes for item in results)


def test_relationship_stack_missing_provenance_is_not_ready() -> None:
    detection = MediaRelationshipCandidateService().detect(
        entities=[
            _entity("track", "collection/song.media", role="media_asset_candidate"),
            _entity("text", "collection/song.text", role="text_sidecar_candidate"),
        ],
        relationship_goal=ContractDrivenPerceptionService().relationship_goal(
            plan=ContractDrivenPerceptionService().contract_observation_plan(_relationship_contract()),
            declared_contract=_relationship_contract(),
        ),
        artifact_contract=_relationship_contract(),
    )
    observation = _observation_payload(detection)
    observation["provenance_trace_id"] = None

    results = RelationshipValidationPolicyService().validate_many(
        relationship_observations=[observation],
        provenance_traces=[],
        evidence_records=[item.model_dump(mode="json") for item in detection["evidence_records"]],
    )

    assert results[0].status == "not_ready"
    assert "RELATIONSHIP_PROVENANCE_MISSING" in results[0].reason_codes


def test_relationship_stack_missing_evidence_record_is_not_ready() -> None:
    detection = MediaRelationshipCandidateService().detect(
        entities=[
            _entity("track", "collection/song.media", role="media_asset_candidate"),
            _entity("text", "collection/song.text", role="text_sidecar_candidate"),
        ],
        relationship_goal=ContractDrivenPerceptionService().relationship_goal(
            plan=ContractDrivenPerceptionService().contract_observation_plan(_relationship_contract()),
            declared_contract=_relationship_contract(),
        ),
        artifact_contract=_relationship_contract(),
    )

    results = RelationshipValidationPolicyService().validate_many(
        relationship_observations=[_observation_payload(detection)],
        provenance_traces=[item.model_dump(mode="json") for item in detection["provenance_traces"]],
        evidence_records=[],
    )

    assert results[0].status == "not_ready"
    assert "RELATIONSHIP_CANONICAL_EVIDENCE_RECORD_MISSING" in results[0].reason_codes


def test_relationship_stack_renderer_materializes_payload_only_without_observing(monkeypatch) -> None:
    runtime = ReadonlyAnalysisArtifactRuntimeService()

    def fail_detector(*_args, **_kwargs):
        raise AssertionError("renderer_called_relationship_detector")

    runtime.perception.relationship_detector.detect = fail_detector
    value, present = runtime._relationship_render_field_value(
        "relationship_validation_status",
        perception_payload={
            "relationship_summary": {
                "candidate_count": 1,
                "relation_families": ["textual_sidecar_candidate"],
                "validation_summary": {"validation_ready_count": 1, "reason_codes": ["RELATIONSHIP_VALIDATION_READY"]},
            },
            "relationship_candidates": [],
            "relationship_observations": [],
            "relationship_provenance_traces": [],
        },
    )

    assert present is True
    assert value == "validation_ready"


def test_relationship_stack_no_registry_match_blocks_before_detector(monkeypatch) -> None:
    service = ContractDrivenPerceptionService(observer_registry=CapabilityRegistry(capabilities={}))

    def fail_detector(*_args, **_kwargs):
        raise AssertionError("detector_bypassed_registry")

    service.relationship_detector.detect = fail_detector
    result = service.compile(
        graph=_graph(
            _entity("track", "collection/song.media", role="media_asset_candidate"),
            _entity("text", "collection/song.text", role="text_sidecar_candidate"),
        ),
        declared_contract=_relationship_contract(),
    )

    assert result.relationship_candidates == []
    assert result.relationship_summary["status"] == "blocked"
    assert result.relationship_summary["reason_codes"] == ["NO_MATCHING_RELATIONSHIP_CAPABILITY"]


def test_relationship_stack_validated_policy_does_not_enable_speaker_truth() -> None:
    detection = MediaRelationshipCandidateService().detect(
        entities=[
            _entity("track", "collection/song.media", role="media_asset_candidate"),
            _entity("text", "collection/song.text", role="text_sidecar_candidate"),
        ],
        relationship_goal=ContractDrivenPerceptionService().relationship_goal(
            plan=ContractDrivenPerceptionService().contract_observation_plan(_relationship_contract()),
            declared_contract=_relationship_contract(),
        ),
        artifact_contract=_relationship_contract(),
    )

    results = RelationshipValidationPolicyService().validate_many(
        relationship_observations=[_observation_payload(detection)],
        provenance_traces=[item.model_dump(mode="json") for item in detection["provenance_traces"]],
        evidence_records=[item.model_dump(mode="json") for item in detection["evidence_records"]],
        policy=RelationshipValidationPolicy(allow_validated_status=True),
    )

    assert results[0].status == "validated"
    assert results[0].truth_eligible is False
    assert results[0].speaker_claim_allowed is False
