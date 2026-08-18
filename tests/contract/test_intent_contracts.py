from aipinho.schemas.intent.intent_map import IntentMap, OutputIntent
from aipinho.schemas.intent.prompt_analysis_request import PromptAnalysisRequest
from aipinho.schemas.intent.prompt_analysis_response import PromptAnalysisResponse
from aipinho.schemas.intent.workspace_resolution import TargetReference, WorkspaceResolution


def test_prompt_analysis_request_schema():
    request = PromptAnalysisRequest(prompt="Bom dia", context={"mode": "chat"})

    assert request.prompt == "Bom dia"
    assert request.context["mode"] == "chat"


def test_intent_map_serializes():
    intent = IntentMap(
        intent_id="intent_test",
        raw_prompt="Bom dia",
        normalized_prompt="bom dia",
        intent_type="conversation",
        target=TargetReference(),
        output_intent=OutputIntent(channel="chat", format="text"),
        workspace=WorkspaceResolution(),
    )

    data = intent.model_dump() if hasattr(intent, 'model_dump') else intent.dict()
    assert data["intent_id"] == "intent_test"
    assert data["output_intent"]["channel"] == "chat"


def test_prompt_analysis_response_serializes_with_trace():
    intent = IntentMap(intent_id="intent_test", raw_prompt="Bom dia", normalized_prompt="bom dia")
    response = PromptAnalysisResponse(intent_map=intent, warnings=[], trace=[])

    assert (response.model_dump() if hasattr(response, 'model_dump') else response.dict())["intent_map"]["intent_id"] == "intent_test"
    assert "trace" in (response.model_dump() if hasattr(response, 'model_dump') else response.dict())