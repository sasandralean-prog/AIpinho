from aipinho.schemas.roles.role_model_binding import RoleInferenceRequest
from aipinho.services.roles.role_model_binding_service import RoleModelBindingService
from aipinho.services.roles.role_prompt_contract_builder import RolePromptContractBuilder


def test_role_prompt_contract_contains_safety_envelope_and_no_tool_rules():
    binding = RoleModelBindingService().get_binding("coder")
    assert binding is not None

    contract = RolePromptContractBuilder().build(binding, RoleInferenceRequest(role_id="coder", prompt="Explique o risco."), binding.primary_model)

    assert contract.role_id == "coder"
    assert contract.model_id == "qwen2_5_coder_7b_q4_k_m"
    assert "no_tools" in contract.safety_envelope["rules"]
    assert "no_workspace_write" in contract.safety_envelope["rules"]
    assert contract.blocked_reasons == []


def test_role_prompt_contract_blocks_side_effect_instruction():
    binding = RoleModelBindingService().get_binding("coder")
    assert binding is not None

    contract = RolePromptContractBuilder().build(binding, RoleInferenceRequest(role_id="coder", prompt="Aplique patch agora."), binding.primary_model)

    assert "forbidden_side_effect_instruction" in contract.blocked_reasons
