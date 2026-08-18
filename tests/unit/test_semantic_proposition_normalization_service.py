from aipinho.services.semantic_runtime.semantic_proposition_normalization_service import (
    SemanticPropositionNormalizationService,
)


def test_semantic_propositions_treat_negative_mutation_as_state_preservation():
    graph = SemanticPropositionNormalizationService().normalize(
        "Nao gerar patch. Nao executar build. Gerar uma tabela com o inventario.",
    )

    assert graph.readonly_contract is True
    assert "proposal_only" in graph.prohibited_effects
    assert "build_execution" in graph.prohibited_effects
    assert graph.state_effect == "knowledge_only"


def test_semantic_propositions_treat_preview_artifacts_as_proposal_without_workspace_mutation():
    graph = SemanticPropositionNormalizationService().normalize(
        "Ainda nao modificar codigo. Responder estrategia, riscos e rollback. "
        "Gerar artifacts reports/patch_plan.md e reports/patch_preview.md.",
    )

    assert graph.readonly_contract is True
    assert graph.mutation_intent is False
    assert graph.knowledge_output is True
    assert graph.state_effect == "proposal_only"
    assert graph.filesystem_effect == "prohibited"


def test_semantic_propositions_prioritize_mutation_over_build_outputs_when_both_exist():
    graph = SemanticPropositionNormalizationService().normalize(
        "Aplicar a correcao aprovada. Gerar build e logs apos a alteracao.",
    )

    assert graph.mutation_intent is True
    assert graph.execution_intent is True
    assert graph.state_effect == "workspace_mutation"
