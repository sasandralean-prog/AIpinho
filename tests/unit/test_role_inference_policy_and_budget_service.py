from aipinho.schemas.roles.role_model_binding import RoleInferenceRequest
from aipinho.services.roles.role_inference_budget_service import RoleInferenceBudgetService
from aipinho.services.roles.role_inference_policy_service import RoleInferencePolicyService
from aipinho.services.roles.role_model_binding_service import RoleModelBindingService


def test_role_inference_policy_enables_governed_chat_role_runtime():
    status = RoleInferencePolicyService().status()

    assert status["enabled"] is True
    assert status["chat_auto_role_inference"] is True
    assert status["tool_calling_enabled"] is False
    allowed_runtime_types = RoleInferencePolicyService().allowed_runtime_types()
    assert "llama_cpp_text" in allowed_runtime_types
    assert {"llama_cpp_vision", "llama_cpp_ocr", "llama_cpp_embedding", "llama_cpp_reranker"}.issubset(allowed_runtime_types)


def test_role_inference_budget_detects_prompt_budget_exceeded():
    binding = RoleModelBindingService().get_binding("coder")
    assert binding is not None
    request = RoleInferenceRequest(role_id="coder", prompt="x" * 13000)

    budget = RoleInferenceBudgetService().calculate(binding, request)

    assert budget.exceeded is True
    assert "prompt_budget_exceeded" in budget.warnings
