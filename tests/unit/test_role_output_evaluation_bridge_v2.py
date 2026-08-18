from aipinho.schemas.models.model_response import ModelResponse, ModelUsage
from aipinho.schemas.roles.role_model_binding import RoleInferenceRequest
from aipinho.services.roles.role_model_binding_service import RoleModelBindingService
from aipinho.services.roles.role_output_evaluation_bridge import RoleOutputEvaluationBridge
from aipinho.services.roles.role_prompt_contract_builder import RolePromptContractBuilder


def test_role_output_evaluation_accepts_safe_text_response():
    binding = RoleModelBindingService().get_binding("coder")
    assert binding is not None
    contract = RolePromptContractBuilder().build(binding, RoleInferenceRequest(role_id="coder", prompt="Explique."), binding.primary_model)
    response = ModelResponse(
        request_id="req_test",
        model_id=binding.primary_model,
        provider_id="llama_cpp_text",
        status="completed",
        content="Safe role output with analysis only. No files were changed.",
        usage=ModelUsage(output_chars=55),
        real_inference=False,
    )

    evaluation = RoleOutputEvaluationBridge().evaluate(response, contract)

    assert evaluation.status in {"accepted", "accepted_with_warnings"}
    assert evaluation.accepted is True
