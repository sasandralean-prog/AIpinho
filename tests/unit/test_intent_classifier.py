from aipinho.schemas.intent.prompt_analysis_request import PromptAnalysisRequest
from aipinho.services.prompt_intelligence.prompt_intelligence_service import PromptIntelligenceService


def analyze(prompt: str):
    return PromptIntelligenceService().analyze(PromptAnalysisRequest(prompt=prompt)).intent_map


def test_conversation():
    intent = analyze("Bom dia, tudo certo?")
    assert intent.intent_type == "conversation"
    assert intent.requires_task is False


def test_self_analysis():
    intent = analyze("Explique sua arquitetura atual")
    assert intent.intent_type == "self_analysis"
    assert intent.actor == "self"
    assert intent.requires_workspace is False


def test_capability_explanation():
    intent = analyze("O que voce consegue fazer?")
    assert intent.intent_type == "capability_explanation"
    assert intent.operation in {"list", "explain"}
    assert intent.requested_actions == []


def test_in_chat_final_report():
    intent = analyze("Faça um report final desta conversa")
    assert intent.intent_type == "in_chat_final_report"
    assert intent.output_intent.channel == "chat"
    assert "write_files" not in intent.requested_actions


def test_artifact_generation():
    intent = analyze("Salve um relatório em reports/final.md")
    assert intent.intent_type == "artifact_generation"
    assert intent.output_intent.channel == "artifact"
    assert "write_files" in intent.requested_actions


def test_readonly_analysis():
    intent = analyze("Explique a arquitetura do projeto C:\\Dev\\AIpinho sem alterar nada")
    assert intent.intent_type == "readonly_analysis"
    assert intent.workspace.path == "C:\\Dev\\AIpinho"
    assert "read_files" in intent.requested_actions


def test_patch_request():
    intent = analyze("Conserte o bug no projeto C:\\Dev\\AIpinho")
    assert intent.intent_type == "patch_request"
    assert "patch_preview" in intent.requested_actions
    assert "apply_patch" in intent.requested_actions


def test_patch_preview_only_does_not_request_apply_or_write():
    intent = analyze(r"Prepare um patch preview governado para o projeto C:\workspace. Ainda nao aplique.")

    assert intent.intent_type == "patch_request"
    assert intent.requested_actions == ["patch_preview"]
    assert intent.ambiguity.requires_clarification is False


def test_approval_gated_write_is_not_reclassified_as_absolute_readonly():
    intent = analyze(r"Aplique a correcao no projeto C:\workspace, mas nao altere nada ate aprovacao explicita.")

    assert intent.intent_type == "patch_request"
    assert "apply_patch" in intent.requested_actions


def test_create_directory_is_filesystem_write_not_patch_or_conversation():
    intent = analyze("Crie uma pasta em C:\\Users\\rafae\\Documents\\TestesIALocal\\NovaPasta")
    assert intent.intent_type == "filesystem_write_request"
    assert intent.requires_task is True
    assert intent.requires_workspace is True


def test_build_artifact_request_is_operational_not_conversation():
    intent = analyze("Gere um APK para o projeto C:\\Users\\rafae\\Documents\\TestesIALocal\\AppTeste")
    assert intent.intent_type == "artifact_build_request"
    assert intent.requires_task is True
    assert intent.object in {"artifact", "project"}


def test_public_fact_query_requires_public_search_path_not_private_rag():
    intent = analyze("Quem e o atual governador do Rio de Janeiro?")
    assert intent.intent_type == "public_fact_query"
    assert intent.requires_task is False
    assert intent.requires_workspace is False
    assert "web_request" in intent.requested_actions


def test_unknown_ambiguous():
    intent = analyze("Arrume tudo")
    assert intent.ambiguity.is_ambiguous is True
    assert intent.ambiguity.requires_clarification is True


def test_readonly_artifact_outputs_stay_readonly_when_effect_is_knowledge_only():
    intent = analyze(
        "Discovery do projeto C:\\Dev\\AIpinho em modo somente leitura. "
        "Nao gerar patch. Nao executar build. Gerar uma tabela em reports/phase1.csv."
    )

    assert intent.intent_type == "readonly_analysis"
    assert intent.semantic_intent_graph.readonly_contract is True
    assert intent.semantic_intent_graph.state_effect == "knowledge_only"
    assert intent.requested_actions == ["read_files"]


def test_build_requests_are_classified_by_effect_not_by_write_actions():
    intent = analyze("Gere um APK para o projeto C:\\Users\\rafae\\Documents\\TestesIALocal\\AppTeste")

    assert intent.intent_type == "artifact_build_request"
    assert intent.semantic_intent_graph.state_effect == "build_execution"
    assert intent.operation_type == "build_run"
