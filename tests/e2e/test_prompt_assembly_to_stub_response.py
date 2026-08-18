from aipinho.schemas.prompts.prompt_assembly import PromptAssemblyRequest
from aipinho.services.models.model_invocation_service import ModelInvocationService
from aipinho.services.prompts.prompt_assembly_service import PromptAssemblyService


def test_prompt_assembly_to_stub_response_end_to_end():
    preview = PromptAssemblyService().preview(
        PromptAssemblyRequest(
            purpose="chat",
            role_id="speaker",
            user_message="Responda apenas ok.",
            output_contract_type="chat_response",
            include_trace=True,
        )
    )
    response = ModelInvocationService().invoke(preview.model_request)
    assert preview.invokes_model is False
    assert response.status == "completed"
    assert response.real_inference is False
    assert "stub_model_used" in response.warnings


def test_chat_endpoint_can_use_stub_without_raw_or_real_inference():
    from fastapi.testclient import TestClient

    from aipinho.app_factory import create_app

    client = TestClient(create_app())
    response = client.post("/api/v1/chat", json={"message": "Ola", "use_model_stub": True})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["real_inference"] is False
    assert data["model_used"] == "stub.default"
    assert "raw" not in data["message"].lower()
