from __future__ import annotations

from aipinho.schemas.models.model_request import ModelRequest
from aipinho.schemas.models.model_response import ModelResponse, ModelUsage
from aipinho.schemas.prompts.prompt_message import PromptMessage
from aipinho.schemas.evaluation.evaluation_result import EvaluationResult
from aipinho.services.models.model_invocation_service import ModelInvocationService


class AcceptingEvaluator:
    def evaluate(self, request) -> EvaluationResult:
        return EvaluationResult(
            evaluation_id="evaluation_test",
            status="accepted",
            score=1.0,
            contract_valid=True,
            safety_valid=True,
            evidence_valid=True,
            format_valid=True,
        )


class RecordingLlamaProvider:
    def __init__(self) -> None:
        self.requests: list[ModelRequest] = []

    def invoke(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        return ModelResponse(
            request_id=request.request_id,
            model_id=request.model_id,
            provider_id=request.provider_id,
            status="completed",
            content="OK",
            usage=ModelUsage(),
            finish_reason="stop",
            real_inference=True,
        )

    def status(self) -> dict[str, object]:
        return {"status": "ok"}


class FakeProviderRegistry:
    def get_provider(self, provider_id: str):
        return type("Provider", (), {"type": "llama_cpp_text"})()


class RecordingInferenceRuntime:
    def __init__(self, provider: RecordingLlamaProvider) -> None:
        self.provider = provider
        self.provider_registry = FakeProviderRegistry()

    def invoke(self, request: ModelRequest) -> ModelResponse:
        return self.provider.invoke(request)

    def status(self) -> dict[str, object]:
        return {"status": "ok"}


def test_role_model_invocation_preserves_real_llama_cpp_text_provider() -> None:
    provider = RecordingLlamaProvider()
    service = ModelInvocationService(evaluator=AcceptingEvaluator(), inference_runtime=RecordingInferenceRuntime(provider))  # type: ignore[arg-type]
    request = ModelRequest(
        model_id="qwen3_1_7b_q6_k",
        provider_id="llama_cpp_text",
        messages=[PromptMessage(role="user", content="Responda apenas: OK")],
        metadata={"purpose": "code_analysis", "role_id": "speaker"},
    )

    response = service.invoke_role_model(request)

    assert response.status == "completed"
    assert provider.requests
    assert provider.requests[0].provider_id == "llama_cpp_text"
