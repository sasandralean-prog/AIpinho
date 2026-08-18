from aipinho.schemas.intent.prompt_analysis_request import PromptAnalysisRequest
from aipinho.services.prompt_intelligence.prompt_intelligence_service import PromptIntelligenceService


def test_detects_explicit_workspace_path():
    intent = PromptIntelligenceService().analyze(PromptAnalysisRequest(prompt="Explique C:\\Dev\\AIpinho")).intent_map

    assert intent.workspace.path == "C:\\Dev\\AIpinho"
    assert intent.workspace.declared is True


def test_detects_forbidden_root_as_protected():
    intent = PromptIntelligenceService().analyze(PromptAnalysisRequest(prompt="Corrija C:\\Windows\\System32")).intent_map

    assert intent.workspace.protected is True


def test_self_analysis_does_not_require_workspace():
    intent = PromptIntelligenceService().analyze(PromptAnalysisRequest(prompt="Explique sua arquitetura atual")).intent_map

    assert intent.requires_workspace is False
    assert intent.workspace.requires_clarification is False


def test_vague_project_requires_clarification():
    intent = PromptIntelligenceService().analyze(PromptAnalysisRequest(prompt="Analise nesse projeto")).intent_map

    assert intent.workspace.requires_clarification is True
    assert intent.ambiguity.requires_clarification is True


def test_active_workspace_context_resolves_operational_prompt_without_literal_path():
    workspace = "C:\\Users\\example\\Documents\\ProjetoAlvo"
    intent = PromptIntelligenceService().analyze(
        PromptAnalysisRequest(
            prompt="Implemente uma correcao minima para a persistencia do projeto e rode os testes aplicaveis.",
            context={"active_workspace": workspace},
        )
    ).intent_map

    assert intent.workspace.path == workspace
    assert intent.workspace.declared is True
    assert intent.workspace.requires_clarification is False
    assert intent.ambiguity.requires_clarification is False
