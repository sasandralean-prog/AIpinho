from __future__ import annotations

from aipinho.services.governance.intent_workspace_scope_service import (
    IntentWorkspaceScopeService,
)
from aipinho.services.orchestration.mission_execution_strategy_service import (
    MissionExecutionStrategyService,
)


def _graph() -> dict:
    return {
        "observational_intent": True,
        "mutation_intent": True,
        "execution_intent": True,
        "readonly_contract": False,
        "state_effect": "workspace_mutation",
        "requested_effects": ["workspace_mutation", "build_execution"],
    }


def test_mobile_repair_prompt_derives_mutable_app_readonly_corpus_and_end_to_end() -> None:
    prompt = (
        r"Autorizo leitura, diagnostico, edicao de codigo, testes, build, commit e git push. "
        r"WORKSPACE DO APP A SER CORRIGIDO: C:\Users\rafae\Documents\PinhoabacaxiMusicasDesktop. "
        r"CORPUS DE MUSICAS PARA TESTES - SOMENTE LEITURA: D:\rafa\novapinhomusic. "
        "Nao modifique o corpus. Investigue e corrija os problemas, execute o build, valide, "
        "faca commit e git push."
    )

    scope = IntentWorkspaceScopeService().resolve(
        prompt=prompt,
        workspace_hint=r"C:\Users\rafae\Documents\PinhoabacaxiMusicasDesktop",
        semantic_graph=_graph(),
    )
    strategy = MissionExecutionStrategyService().resolve(
        prompt=prompt,
        semantic_graph=_graph(),
    )

    assert strategy.mode == "end_to_end_governed"
    assert strategy.auto_continue is True
    assert strategy.requires_new_prompt_between_phases is False

    app = next(
        item
        for item in scope["scopes"]
        if item["path"].endswith("PinhoabacaxiMusicasDesktop")
    )
    corpus = next(
        item
        for item in scope["scopes"]
        if item["path"].endswith("novapinhomusic")
    )

    assert app["role"] == "target_mutable"
    assert app["readonly"] is False
    assert "modify_file" in app["declared_permissions"]
    assert "apply_patch" in app["declared_permissions"]
    assert "shell_build" in app["declared_permissions"]
    assert "git_commit" in app["declared_permissions"]
    assert "git_push" in app["declared_permissions"]

    assert corpus["role"] == "source_readonly"
    assert corpus["readonly"] is True
    assert corpus["declared_permissions"] == ["copy_from", "list_files", "read_file"]
    assert r"D:\rafa\novapinhomusic" in scope["readonly_roots"]
    assert r"D:\rafa\novapinhomusic" in scope["library_roots"]
    assert scope["readonly_flags"][r"D:\rafa\novapinhomusic"] is True


def test_prompt_that_requests_analysis_then_waits_is_staged() -> None:
    prompt = (
        r"Analise C:\Work\App e me mostre o diagnostico antes de alterar. "
        "Aguarde minha confirmacao e nao execute o patch agora."
    )
    strategy = MissionExecutionStrategyService().resolve(
        prompt=prompt,
        semantic_graph=_graph(),
    )

    assert strategy.mode == "staged"
    assert strategy.auto_continue is False
    assert strategy.requires_new_prompt_between_phases is True
    assert strategy.stop_at_approval_gate is True


def test_readonly_prompt_without_side_effects_is_single_operation() -> None:
    strategy = MissionExecutionStrategyService().resolve(
        prompt=r"Analise C:\Work\App somente leitura.",
        semantic_graph={
            "observational_intent": True,
            "mutation_intent": False,
            "execution_intent": False,
            "readonly_contract": True,
            "requested_effects": ["knowledge_only"],
        },
    )

    assert strategy.mode == "single_operation"
    assert strategy.auto_continue is False
