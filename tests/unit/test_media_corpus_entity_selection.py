from pathlib import Path

from aipinho.services.artifacts.observed_entity_compilation_service import ObservedEntityCompilationService
from aipinho.services.artifacts.semantic_artifact_intent_resolver import SemanticArtifactIntentResolver
from aipinho.services.artifacts.semantic_entity_selection_service import SemanticEntitySelectionService


def test_entity_selection_uses_root_role_entity_role_and_evidence(tmp_path: Path) -> None:
    project = tmp_path / "app"
    library = tmp_path / "library"
    (project / "src").mkdir(parents=True)
    library.mkdir()
    (project / "src" / "Main.any").write_text("project", encoding="utf-8")
    (library / "Track.any").write_text("media", encoding="utf-8")
    observed = ObservedEntityCompilationService()
    graph = observed.compile(
        workspace=str(project),
        workspace_context={"project_root": str(project), "library_roots": [str(library)]},
    ).model_dump(mode="json")
    plan = SemanticArtifactIntentResolver().resolve(
        prompt="Inventariar biblioteca de audio.",
        declared_contract={"expected_kind": "tabular_collection", "expected_schema": ["entity_id", "source_root_role", "evidence_ref"]},
        workspace_context={"library_roots": [str(library)]},
    )

    result = SemanticEntitySelectionService().select(graph=graph, intent=plan, max_entities=10)

    assert result.expected_rows == 1
    assert result.selected_rows == 1
    assert result.bound_rows == 1
    assert result.evidence_ref_count == 1
    assert result.root_roles_selected == {"library_root": 1}
    assert result.rejection_reasons["ROOT_ROLE_NOT_ALLOWED"] >= 1


def test_entity_selection_blocks_without_minimum_evidence_ref() -> None:
    plan = SemanticArtifactIntentResolver().resolve(
        prompt="Inventariar biblioteca de audio.",
        declared_contract={"expected_kind": "tabular_collection", "expected_schema": ["entity_id", "source_root_role", "evidence_ref"]},
        workspace_context={"library_roots": ["X:/library"]},
    )
    graph = {
        "entities": [
            {
                "entity_id": "entity_1",
                "entity_kind": "file",
                "source_root_role": "library_root",
                "relative_path": "Track.any",
                "entity_role": "corpus_file",
                "selection_eligibility": {"corpus_inventory": True},
                "observed_attributes": {},
                "evidence_refs": [],
            }
        ]
    }

    result = SemanticEntitySelectionService().select(graph=graph, intent=plan, max_entities=10)

    assert result.status == "blocked"
    assert result.reason_code == "MUSIC_INVENTORY_ENTITY_BINDING_INSUFFICIENT"
    assert result.bound_rows == 0
    assert result.rejection_reasons["ENTITY_EVIDENCE_REF_MISSING"] == 1
