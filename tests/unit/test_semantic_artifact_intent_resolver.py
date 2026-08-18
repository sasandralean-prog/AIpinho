from aipinho.services.artifacts.semantic_artifact_intent_resolver import SemanticArtifactIntentResolver


def test_prompt_meaning_resolves_media_corpus_inventory_without_path_authority() -> None:
    plan = SemanticArtifactIntentResolver().resolve(
        prompt="Inventariar a biblioteca de audio e catalogar as faixas com evidencias.",
        declared_contract={"expected_kind": "tabular_collection", "expected_schema": ["entity_id", "evidence_ref"]},
        workspace_context={"library_roots": ["X:/corpus"]},
        artifact_logical_path="reports/output.csv",
    )

    assert plan.artifact_kind == "media_corpus_inventory"
    assert plan.semantic_domain == "media_corpus"
    assert plan.source_root_roles_required == ["library_root", "corpus_root"]
    assert "prompt_semantics" in plan.resolution_sources
    assert plan.metadata["path_hint_authority"] is False


def test_logical_path_hint_alone_does_not_create_media_inventory_authority() -> None:
    plan = SemanticArtifactIntentResolver().resolve(
        prompt="Gerar relatorio tabular generico.",
        declared_contract={"expected_kind": "tabular_collection", "expected_schema": ["summary"]},
        workspace_context={},
        artifact_logical_path="reports/music_inventory.csv",
    )

    assert plan.semantic_domain == "generic"
    assert plan.metadata.get("path_hint_authority") is None


def test_declared_semantic_contract_is_authority_even_with_neutral_prompt() -> None:
    plan = SemanticArtifactIntentResolver().resolve(
        prompt="Gerar o CSV solicitado.",
        declared_contract={
            "contract_id": "media_corpus_inventory_artifact",
            "expected_kind": "tabular_collection",
            "expected_schema": ["entity_id", "source_root_role", "evidence_ref"],
            "expected_semantics": {"media_corpus_inventory_required": True},
        },
        workspace_context={"library_roots": ["X:/corpus"]},
        artifact_logical_path="reports/output.csv",
    )

    assert plan.artifact_kind == "media_corpus_inventory"
    assert "artifact_semantic_contract" in plan.resolution_sources
