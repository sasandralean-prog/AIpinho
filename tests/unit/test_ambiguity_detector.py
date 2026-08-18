from aipinho.schemas.intent.prompt_analysis_request import PromptAnalysisRequest
from aipinho.services.prompt_intelligence.prompt_intelligence_service import PromptIntelligenceService


def test_casual_prompt_is_not_ambiguous():
    intent = PromptIntelligenceService().analyze(PromptAnalysisRequest(prompt="Bom dia, tudo certo?")).intent_map

    assert intent.ambiguity.is_ambiguous is False


def test_arrume_tudo_is_ambiguous():
    intent = PromptIntelligenceService().analyze(PromptAnalysisRequest(prompt="Arrume tudo")).intent_map

    assert intent.ambiguity.is_ambiguous is True
    assert "contextual_ambiguity_marker" in intent.ambiguity.reasons


def test_ambiguity_light_only_with_operational_context():
    service = PromptIntelligenceService()
    casual = service.analyze(PromptAnalysisRequest(prompt="Bom dia, tudo certo?")).intent_map
    operational = service.analyze(PromptAnalysisRequest(prompt="Arrume tudo")).intent_map

    assert casual.ambiguity.is_ambiguous is False
    assert operational.ambiguity.is_ambiguous is True


def test_deferred_creation_language_is_not_operational_ambiguity():
    intent = PromptIntelligenceService().analyze(
        PromptAnalysisRequest(prompt="Sugira uma ideia de aplicativo para eu criar depois.")
    ).intent_map

    assert intent.intent_type == "conversation"
    assert intent.requires_task is False
    assert intent.ambiguity.is_ambiguous is False
