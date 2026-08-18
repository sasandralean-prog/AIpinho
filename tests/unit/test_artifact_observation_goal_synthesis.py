from pathlib import Path

from aipinho.services.artifacts.contract_driven_perception_service import ContractDrivenPerceptionService
from aipinho.services.artifacts.observed_entity_compilation_service import ObservedEntityCompilationService


def test_artifact_contract_synthesizes_observation_goals_for_media_inventory(tmp_path: Path) -> None:
    project = tmp_path / "app"
    library = tmp_path / "library"
    project.mkdir()
    library.mkdir()
    (library / "Track.any").write_text("media", encoding="utf-8")
    observed = ObservedEntityCompilationService()
    graph = observed.compile(
        workspace=str(project),
        workspace_context={"project_root": str(project), "library_roots": [str(library)]},
    ).model_dump(mode="json")

    result = ContractDrivenPerceptionService(observed_entities=observed).compile(
        graph=graph,
        declared_contract={
            "contract_id": "media_corpus_inventory_artifact",
            "expected_kind": "tabular_collection",
            "expected_schema": ["entity_id", "source_root_role", "relative_path", "evidence_ref"],
            "workspace_context": {"project_root": str(project), "library_roots": [str(library)]},
        },
    )

    goals = result.observation_plan.observation_goals
    assert goals
    assert {goal.canonical_key for goal in goals} >= {"entity_id", "source_root_role", "relative_path"}
    assert all(goal.entity_ref["source_root_roles"] == ["library_root"] for goal in goals)
    assert all(goal.evidence_refs for goal in goals)
