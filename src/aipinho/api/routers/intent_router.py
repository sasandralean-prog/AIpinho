from __future__ import annotations

from fastapi import APIRouter

from aipinho.core.paths import PATHS
from aipinho.schemas.intent.prompt_analysis_request import PromptAnalysisRequest
from aipinho.services.prompt_intelligence.intent_classifier import IntentClassifier
from aipinho.services.prompt_intelligence.prompt_intelligence_service import PromptIntelligenceService
from aipinho.utils.yaml_loader import load_yaml_file

router = APIRouter(prefix="/api/v1/intent", tags=["intent"])


@router.get("/status")
def get_intent_status() -> dict[str, object]:
    return PromptIntelligenceService().status()


@router.get("/taxonomy")
def get_intent_taxonomy() -> dict[str, object]:
    data = load_yaml_file(PATHS.config_root / "policies" / "intent_taxonomy.yaml", critical=True, root=PATHS.config_root / "policies")
    return {"status": "ok", "taxonomy": data.get("intents", {})}


@router.post("/analyze")
def analyze_intent(request: PromptAnalysisRequest):
    return PromptIntelligenceService().analyze(request)


@router.post("/contract-preview")
def preview_intent_contract(request: PromptAnalysisRequest):
    return PromptIntelligenceService().contract_preview(request)