from aipinho.schemas.roles.effective_role_policy import EffectiveRolePolicy
from aipinho.schemas.roles.role_definition import RoleDefinition
from aipinho.schemas.roles.role_model_gate import RoleModelGateDecision
from aipinho.schemas.roles.role_pass import RolePass
from aipinho.schemas.roles.role_pass_output import RolePassOutput


def test_role_contracts_construct():
    role = RoleDefinition(purpose="x")
    assert role.can_call_tools is False
    policy = EffectiveRolePolicy(role_id="speaker", allowed=True)
    assert policy.can_write is False
    gate = RoleModelGateDecision(role_id="speaker", status="allowed", allowed=True)
    assert gate.real_inference is False
    output = RolePassOutput(role_id="speaker", status="completed", content="ok")
    role_pass = RolePass(pass_id="p", role_id="speaker", output=output)
    assert role_pass.output.content == "ok"
