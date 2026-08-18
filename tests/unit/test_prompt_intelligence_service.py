from aipinho.schemas.intent.prompt_analysis_request import PromptAnalysisRequest
from aipinho.core.paths import PATHS
from aipinho.services.prompt_intelligence.prompt_intelligence_service import PromptIntelligenceService
from aipinho.utils.yaml_loader import load_yaml_file


CASES = [
    ("Bom dia, tudo certo?", "conversation"),
    ("Explique sua arquitetura atual", "self_analysis"),
    ("O que voce consegue fazer?", "capability_explanation"),
    ("Faça um report final desta conversa", "in_chat_final_report"),
    ("Salve um relatório em reports/final.md", "artifact_generation"),
    ("Explique a arquitetura do projeto C:\\Dev\\AIpinho sem alterar nada", "readonly_analysis"),
    ("Conserte o bug no projeto C:\\Dev\\AIpinho", "patch_request"),
]


def test_mandatory_cases():
    service = PromptIntelligenceService()
    for prompt, expected in CASES:
        intent = service.analyze(PromptAnalysisRequest(prompt=prompt)).intent_map
        assert intent.intent_type == expected
        assert intent.trace
        assert intent.evidence or expected == "conversation"


def test_forbidden_root_case():
    config_path = PATHS.config_root / "workspaces" / "protected_workspaces.yaml"
    config = load_yaml_file(config_path, critical=True, root=config_path.parent)
    protected_path = next(
        str(item["path"])
        for item in config.get("protected_roots", [])
        if isinstance(item, dict) and item.get("block_task", False)
    )
    intent = PromptIntelligenceService().analyze(PromptAnalysisRequest(prompt=f"Corrija {protected_path}")).intent_map

    assert intent.workspace.protected is True
    assert intent.risk.level == "critical"


def test_theoretical_coding_question_is_not_patch_request():
    intent = PromptIntelligenceService().analyze(PromptAnalysisRequest(prompt="Como consertar arquitetura em teoria?")).intent_map

    assert intent.intent_type == "conversation"
    assert intent.output_intent.channel == "chat"
    assert "write_files" not in intent.requested_actions


def test_no_write_constraint_takes_precedence_over_mutation_term_for_analysis():
    intent = PromptIntelligenceService().analyze(
        PromptAnalysisRequest(
            prompt='Analise o projeto em "C:\\Users\\example\\Documents\\Projeto" e nao altere arquivos.',
        ),
    ).intent_map

    assert intent.intent_type == "readonly_analysis"
    assert intent.task_type == "readonly_analysis"
    assert intent.requested_actions == ["read_files"]
    assert intent.requires_approval is False


def test_project_repair_with_report_output_is_patch_request_not_artifact_build():
    intent = PromptIntelligenceService().analyze(
        PromptAnalysisRequest(
            prompt=(
                "Com base no diagnostico anterior, implemente uma correcao minima para a persistencia "
                "do projeto. Rode test/build/check quando aplicavel e gere relatorio em reports/fix.md."
            ),
            context={"active_workspace": "C:\\Users\\example\\Documents\\ProjetoAlvo"},
        )
    ).intent_map

    assert intent.intent_type == "patch_request"
    assert intent.task_type == "patch_request"
    assert intent.workspace.path == "C:\\Users\\example\\Documents\\ProjetoAlvo"
    assert "patch_preview" in intent.requested_actions
    assert "apply_patch" in intent.requested_actions
    assert "write_files" in intent.requested_actions
