from fastapi.testclient import TestClient

from aipinho.app_factory import create_app
from aipinho.schemas.models.model_request import ModelRequest
from aipinho.schemas.prompts.prompt_assembly import PromptAssemblyRequest
from aipinho.schemas.prompts.prompt_context_item import PromptContextItem, PromptContextSafety
from aipinho.schemas.prompts.prompt_message import PromptMessage
from aipinho.services.models.model_invocation_service import ModelInvocationService
from aipinho.services.prompts.prompt_assembly_service import PromptAssemblyService

client = TestClient(create_app())


def test_default_status_reports_governed_real_runtime():
    data = client.get("/api/v1/models/status").json()
    assert data["default_model"] == "qwen3_1_7b_q6_k"
    assert data["real_inference_enabled"] is True
    assert data["llama_cpp_provider_enabled"] is True


def test_validate_forbidden_and_non_gguf_paths_blocked():
    forbidden = client.post("/api/v1/models/llama-cpp/validate", json={"model_path": "C:\\PinhoabacaxiAI\\model.gguf"}).json()
    assert "outside_allowed_model_roots" in forbidden["environment"]["model"]["blocked_reasons"]
    non_gguf = client.post("/api/v1/models/llama-cpp/validate", json={"model_path": "C:\\AI\\models\\model.bin"}).json()
    assert "invalid_extension" in non_gguf["environment"]["model"]["blocked_reasons"]


def test_invoke_with_opt_in_is_controlled_when_runtime_input_is_incomplete():
    data = client.post("/api/v1/models/llama-cpp/invoke", json={"prompt": "Ola", "allow_real_inference": True, "manual_mode": True}).json()
    assert data["status"] == "blocked"
    assert data["process_started"] is False
    assert set(data["response"]["warnings"]) & {"provider_disabled_or_not_real_inference", "model_disabled_or_not_real_inference", "model_path_invalid", "executable_invalid"}


def test_disabled_model_via_model_invocation_service_blocked():
    request = ModelRequest(model_id="llama.local.placeholder", provider_id="llama_cpp.local", messages=[PromptMessage(role="user", content="Ola")])
    response = ModelInvocationService().invoke(request)
    assert response.status == "blocked"
    assert response.real_inference is False


def test_stub_still_works():
    data = client.post("/api/v1/models/invoke-stub", json={"prompt": "Ola"}).json()
    assert data["response"]["status"] == "completed"
    assert data["response"]["real_inference"] is False


def test_prompt_assembly_for_llama_preserves_safety_and_omits_secret():
    preview = PromptAssemblyService().preview(
        PromptAssemblyRequest(
            purpose="chat",
            role_id="speaker",
            user_message="Ola",
            model_id="llama.local.placeholder",
            output_contract_type="chat_response",
            context_items=[PromptContextItem(source_type="file", title="secret", content="token=abc", safety=PromptContextSafety(contains_secret=True))],
        )
    )
    assert preview.model_request.safety_envelope
    assert preview.model_request.output_contract
    assert preview.model_request.metadata["budget_summary"]
    assert all("token=abc" not in message.content for message in preview.model_request.messages)


def test_chat_can_use_governed_real_default_for_normal_prompt():
    data = client.post("/api/v1/chat", json={"message": "Ola"}).json()
    assert data["model_used"] == "qwen3_1_7b_q6_k"
    assert data["real_inference"] is True


def test_user_asks_real_model_in_chat_gets_governed_selection_guidance():
    data = client.post("/api/v1/chat", json={"message": "use modelo llama real"}).json()
    assert data["status"] == "preview"
    assert data["real_inference"] is False
    assert "modelo" in data["message"].lower()
    assert "direct_model_selection_requires_policy" in data["warnings"]


def test_network_or_download_like_model_path_blocked():
    data = client.post("/api/v1/models/llama-cpp/validate", json={"model_path": "https://example.com/model.gguf"}).json()
    assert "network_path_blocked" in data["environment"]["model"]["blocked_reasons"]
