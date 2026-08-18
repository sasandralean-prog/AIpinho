from aipinho.schemas.intent.prompt_analysis_request import PromptAnalysisRequest
from aipinho.services.prompt_intelligence.prompt_intelligence_service import PromptIntelligenceService


def level(prompt: str) -> str:
    return PromptIntelligenceService().analyze(PromptAnalysisRequest(prompt=prompt)).intent_map.risk.level


def test_self_analysis_is_low_risk():
    assert level("Explique sua arquitetura atual") == "low"


def test_readonly_is_medium_risk():
    assert level("Explique a arquitetura do projeto C:\\Dev\\AIpinho sem alterar nada") == "medium"


def test_artifact_is_high_risk():
    assert level("Salve um relatório em reports/final.md") == "high"


def test_patch_is_critical_due_apply_patch():
    assert level("Conserte o bug no projeto C:\\Dev\\AIpinho") == "critical"


def test_forbidden_root_is_critical():
    assert level("Corrija C:\\PinhoabacaxiAI") == "critical"