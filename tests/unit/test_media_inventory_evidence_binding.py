from aipinho.schemas.artifacts.semantic_artifact_intent import ArtifactIntentPlan
from aipinho.services.artifacts.semantic_entity_selection_service import SemanticEntitySelectionService


def test_media_inventory_row_requires_evidence_ref_to_be_safe_to_use() -> None:
    intent = ArtifactIntentPlan(
        artifact_kind="media_corpus_inventory",
        semantic_domain="media_corpus",
        source_root_roles_required=["library_root", "corpus_root"],
        required_entity_types=["file"],
        required_entity_roles=["corpus_file"],
        required_attributes=["entity_id", "source_root_role", "relative_path", "evidence_ref"],
        required_evidence_types=["entity_identity", "root_role", "source_path", "observation_provenance"],
        block_reason_if_missing="MUSIC_INVENTORY_ENTITY_BINDING_INSUFFICIENT",
    )
    graph = {
        "entities": [
            {
                "entity_id": "entity_1",
                "entity_kind": "file",
                "source_root_role": "library_root",
                "entity_role": "corpus_file",
                "relative_path": "Track.any",
                "selection_eligibility": {"corpus_inventory": True},
                "evidence_refs": ["file:X:/library/Track.any"],
            }
        ]
    }

    result = SemanticEntitySelectionService().select(graph=graph, intent=intent, max_entities=10)

    assert result.bound_rows == 1
    assert result.evidence_ref_count == 1
    row = result.rows[0]
    assert row["safe_to_use"] is True
    assert row["truth_eligible"] is False
    assert row["evidence_refs"] == ["file:X:/library/Track.any"]
