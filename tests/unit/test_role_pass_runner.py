from aipinho.schemas.roles.role_pass_input import RolePassInput
from aipinho.services.roles.role_pass_runner import RolePassRunner


def test_role_pass_runner_runs_speaker_with_stub():
    result = RolePassRunner().run(RolePassInput(role_id="speaker", user_message="Ola", policy_decision={"status": "allowed"}))
    assert result.status == "completed"
    assert result.output.source == "stub"
    assert result.model_gate.real_inference is False


def test_role_pass_runner_deterministic_supervisor_does_not_call_model():
    result = RolePassRunner().run(RolePassInput(role_id="supervisor", user_message="verifique", purpose="validation", policy_decision={"status": "allowed"}))
    assert result.status == "completed"
    assert result.output.source == "deterministic"
    assert result.model_gate.status == "deterministic_only"


def test_role_pass_runner_blocks_denied_policy():
    result = RolePassRunner().run(RolePassInput(role_id="speaker", user_message="Ola", policy_decision={"status": "denied"}))
    assert result.status == "rejected"
    assert result.output.source == "fallback"
