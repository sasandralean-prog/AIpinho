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

def test_build_directory_exclusion_is_not_build_execution_prohibition():
    graph = SemanticPropositionNormalizationService().normalize(
        "Corrija o codigo e execute o build. Nao versione build, caches ou artefatos transitorios.",
    )

    assert graph.mutation_intent is True
    assert graph.execution_intent is True
    assert "build_execution" in graph.requested_effects
    assert "build_execution" not in graph.prohibited_effects

def test_long_mission_scopes_corpus_write_prohibition_without_blocking_workspace_or_build():
    graph = SemanticPropositionNormalizationService().normalize(
        "Autorizo edicao de codigo, execucao de Gradle/build/test e git push, desde que nao masque falhas. "
        r"WORKSPACE DO APP: C:\Users\rafae\Documents\PinhoabacaxiMusicasDesktop. "
        r"CORPUS SOMENTE LEITURA: D:\rafa\novapinhomusic. "
        "Nao modifique o corpus. Investigue e corrija o codec no workspace. "
        "Execute o build e valide. Nao versione build, caches, secrets ou artefatos transitorios."
    )

    assert graph.mutation_intent is True
    assert graph.execution_intent is True
    assert "workspace_mutation" in graph.requested_effects
    assert "build_execution" in graph.requested_effects
    assert "workspace_mutation" not in graph.prohibited_effects
    assert "build_execution" not in graph.prohibited_effects
    assert graph.filesystem_effect == "mutable"
    assert graph.runtime_effect != "prohibited"
    assert "scoped_negative:workspace_mutation" in graph.evidence


def test_windows_drive_scoped_write_prohibition_does_not_become_global() -> None:
    graph = SemanticPropositionNormalizationService().normalize(
        "Edite e corrija o codigo no workspace alvo. "
        r"Nao modifique D:\media\readonly_corpus. "
        "Execute testes e build depois da alteracao."
    )

    assert graph.mutation_intent is True
    assert graph.execution_intent is True
    assert "workspace_mutation" in graph.requested_effects
    assert "workspace_mutation" not in graph.prohibited_effects
    assert graph.filesystem_effect == "mutable"
    assert "scoped_negative:workspace_mutation" in graph.evidence
