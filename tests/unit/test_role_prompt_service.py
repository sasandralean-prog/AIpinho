from aipinho.schemas.roles.effective_role_policy import EffectiveRolePolicy
from aipinho.schemas.roles.role_pass_input import RolePassInput
from aipinho.services.roles.role_prompt_service import RolePromptService


def test_role_prompt_service_includes_contract_and_safety():
    effective = EffectiveRolePolicy(role_id="speaker", allowed=True, can_call_model=True, model_policy="stub_only", output_contract="chat_response")
    preview = RolePromptService().preview(RolePassInput(role_id="speaker", user_message="Ola"), effective)
    assert preview.invokes_model is False
    assert preview.assembly.output_contract.contract_type == "chat_response"
    assert preview.assembly.safety_envelope.rules
