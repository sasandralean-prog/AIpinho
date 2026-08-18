from __future__ import annotations

from aipinho.services.artifacts.artifact_semantic_contract_service import ArtifactSemanticContractService
from aipinho.services.artifacts.contract_driven_perception_service import ContractDrivenPerceptionService
from aipinho.services.artifacts.media_relationship_candidate_service import MediaRelationshipCandidateService
from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import ReadonlyAnalysisArtifactRuntimeService
from aipinho.services.runtime.universal_task_session_service import UniversalTaskSessionService

from tests.unit.test_media_relationship_foundation import _entity, _graph


def _relationship_detection() -> dict:
    return MediaRelationshipCandidateService().detect(
        entities=[
            _entity("track", "album/song.media", role="media_asset_candidate"),
            _entity("text", "album/song.text", role="text_sidecar_candidate"),
        ],
        relationship_goal=ContractDrivenPerceptionService().relationship_goal(
            plan=ContractDrivenPerceptionService().contract_observation_plan(
                {
                    "contract_id": "generic_relationship_contract",
                    "expected_kind": "tabular_collection",
                    "expected_schema": ["name"],
                    "expected_relationships": [{"family": "textual_sidecar_candidate"}],
                    "relationship_goal": {"allowed_relation_families": ["textual_sidecar_candidate"]},
                }
            ),
            declared_contract={
                "expected_relationships": [{"family": "textual_sidecar_candidate"}],
                "relationship_goal": {"allowed_relation_families": ["textual_sidecar_candidate"]},
            },
        ),
        artifact_contract={"contract_id": "generic_relationship_contract", "expected_relationships": [{}]},
    )


def test_artifact_contract_derives_relationship_fields_from_profile_binding() -> None:
    detection = _relationship_detection()
    candidate = detection["candidates"][0]
    observation = detection["observations"][0]
    service = ArtifactSemanticContractService()

    result = service.validate(
        logical_path="reports/entities.csv",
        content_type="text/csv",
        content="name\nsong\n",
        declared_contract={
            "expected_kind": "tabular_collection",
            "expected_schema": ["name"],
            "expected_relationships": [{"family": "textual_sidecar_candidate"}],
            "relationship_fields": [
                "relationship_candidate_count",
                "relationship_top_family",
                "relationship_validation_status",
                "relationship_evidence_ref_count",
                "relationship_provenance_ref_count",
            ],
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
                        "truth_eligible": False,
                        "validation_required": True,
                    }
                ],
                "relationship_provenance_traces": [item.model_dump(mode="json") for item in detection["provenance_traces"]],
            },
        },
    )

    assert result.status == "blocked"
    assert result.profile is not None
    assert result.profile.relationship_rendered_fields["relationship_candidate_count"] == 1
    assert result.profile.relationship_rendered_fields["relationship_top_family"] == "textual_sidecar_candidate"
    assert result.profile.relationship_rendered_fields["relationship_validation_status"] == "validation_required"
    assert result.profile.relationship_rendering_summary["truth_eligible"] is False
    assert result.profile.relationship_rendering_summary["rendered_field_count"] == 5
    assert result.profile.relationship_rendering_summary["truth_eligible"] is False


def test_runtime_renderer_materializes_relationship_fields_without_calling_detector() -> None:
    graph = _graph(
        _entity("track", "album/song.media", role="media_asset_candidate"),
        _entity("text", "album/song.text", role="text_sidecar_candidate"),
    )
    runtime = ReadonlyAnalysisArtifactRuntimeService()
    render = runtime._contract_tabular_collection_content(
        expected_schema=[
            "name",
            "relationship_candidate_count",
            "relationship_top_family",
            "relationship_validation_status",
            "relationship_evidence_ref_count",
        ],
        analysis_payload={"observed_entity_graph": graph},
        declared_contract={
            "contract_id": "generic_relationship_contract",
            "expected_kind": "tabular_collection",
            "expected_schema": [
                "name",
                "relationship_candidate_count",
                "relationship_top_family",
                "relationship_validation_status",
                "relationship_evidence_ref_count",
            ],
            "expected_relationships": [{"family": "textual_sidecar_candidate"}],
            "relationship_goal": {"allowed_relation_families": ["textual_sidecar_candidate"]},
            "entity_selection_contract": {"allowed_root_roles": ["library_root"]},
        },
        run_id="relationship_render_test",
    )

    assert "relationship_candidate_count" in render.content
    assert "relationship_top_family" in render.content
    assert "validation_required" in render.content
    assert render.entity_summary["perception"]["relationship_rendering"]["rendered_field_count"] >= 1
    assert render.entity_summary["perception"]["relationship_rendering"]["truth_eligible"] is False
    assert any(item.get("reason_code") == "RELATIONSHIP_VALIDATION_REQUIRED" for item in render.semantic_gaps)


def test_relationship_cognition_summary_reports_rendered_fields_lightly() -> None:
    summary = UniversalTaskSessionService()._relationship_cognition_summary(
        [{"candidate_count": 1, "observation_count": 1, "evidence_count": 3, "relation_families": ["textual_sidecar_candidate"]}],
        [],
        [{"rendered_field_count": 4, "evidence_ref_count": 3, "provenance_ref_count": 1, "validation_status": "validation_required"}],
    )

    assert summary["candidate_count"] == 1
    assert summary["rendered_field_count"] == 4
    assert summary["evidence_ref_count"] == 3
    assert summary["provenance_ref_count"] == 1
    assert summary["truth_eligible"] is False
    assert summary["validation_status"] == "validation_required"
