from types import SimpleNamespace

from aipinho.schemas.chat.manual_chat_inference_request import ManualChatInferenceRequest
from aipinho.schemas.models.model_response import ModelResponse
from aipinho.services.chat.chat_manual_inference_service import ChatManualInferenceService
from aipinho.services.prompts.prompt_assembly_service import PromptAssemblyService


class FakePolicy:
    manual_chat = {"output_contract_type": "chat_response", "safety_envelope_id": "local_manual_inference"}
    def validate_request(self, request):
        return {"allowed": True, "warnings": [], "blocked_reasons": [], "manual_gate_decision": {"allowed": True, "status": "allowed"}, "profile": SimpleNamespace(profile_id=request.profile_id, output_contract_type="chat_response", safety_envelope_id="local_manual_inference", temperature=0.0, top_p=1.0, max_output_tokens=64, timeout_seconds=10, ctx_size=1024)}
    def status(self):
        return {"status": "ok"}


class FakeLlama:
    def invoke_preview(self, request):
        return {"status": "ok", "process_started": False, "gate_decision": {"allowed": True, "status": "allowed"}}


class FakeInvocation:
    llama_cpp = FakeLlama()
    def invoke(self, request):
        return ModelResponse(request_id=request.request_id, model_id=request.model_id, provider_id=request.provider_id, status="completed", content="Resposta manual segura.", real_inference=True, evaluation_result={"status": "accepted", "score": 1.0, "warnings": [], "violations": [], "fallback_decision": {"should_fallback": False}})


def _service():
    return ChatManualInferenceService(policy_service=FakePolicy(), prompt_assembly_service=PromptAssemblyService(), model_invocation_service=FakeInvocation())


def test_manual_inference_preview_never_starts_process():
    response = _service().preview(ManualChatInferenceRequest(message="Ola", allow_real_inference=True, operator_confirmed=True))
    assert response.status == "preview"
    assert response.process_started is False
    assert response.real_inference is False


def test_manual_inference_run_uses_model_only_when_policy_allows():
    response = _service().run(ManualChatInferenceRequest(message="Ola", allow_real_inference=True, operator_confirmed=True))
    assert response.status == "ok"
    assert response.real_inference is True
    assert response.message == "Resposta manual segura."
