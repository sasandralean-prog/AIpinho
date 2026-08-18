from aipinho.schemas.roles.role_model_gate import RoleModelGateRequest
from aipinho.services.roles.role_model_gate_service import RoleModelGateService


def _request(**kw):
    base = {"role_id": "analyst", "model_policy": "stub_only", "requested_model_id": "stub.default", "purpose": "code_analysis", "output_contract": {"contract_type": "json_findings"}, "safety_envelope": {"rules": ["no_tools"]}}
    base.update(kw)
    return RoleModelGateRequest(**base)


def test_role_model_gate_stub_allowed():
    decision = RoleModelGateService().decide(_request())
    assert decision.allowed is True
    assert decision.real_inference is False


def test_role_model_gate_real_model_blocked():
    decision = RoleModelGateService().decide(_request(requested_model_id="llama.local.placeholder"))
    assert decision.allowed is False
    assert any(reason in decision.blocked_reasons for reason in {"model_not_allowed_by_role_policy", "model_disabled", "provider_disabled"})


def test_role_model_gate_deterministic_only_no_model_invocation():
    decision = RoleModelGateService().decide(_request(role_id="supervisor", model_policy="deterministic_only", requested_model_id=None))
    assert decision.status == "deterministic_only"
    assert decision.allowed is False


def test_role_model_gate_missing_contract_blocks():
    decision = RoleModelGateService().decide(_request(output_contract={}))
    assert decision.allowed is False
    assert "missing_output_contract" in decision.blocked_reasons
