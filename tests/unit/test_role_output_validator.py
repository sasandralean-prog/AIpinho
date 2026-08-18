from aipinho.schemas.roles.role_pass_output import RolePassOutput
from aipinho.services.roles.role_output_validator import RoleOutputValidator


def test_role_output_validator_accepts_plain_text():
    output = RolePassOutput(role_id="speaker", status="completed", content="Resposta segura.")
    result = RoleOutputValidator().validate(output, output_contract={"contract_type": "chat_response", "format": "markdown"}, safety_envelope={"rules": ["no_tools"]})
    assert result["valid"] is True


def test_role_output_validator_rejects_missing_evidence_for_analyst():
    output = RolePassOutput(role_id="analyst", status="completed", content='{"findings": [], "limitations": []}')
    result = RoleOutputValidator().validate(output, output_contract={"contract_type": "json_findings", "format": "json"}, safety_envelope={"rules": ["no_tools"]}, evidence=[])
    assert result["valid"] is False
    assert "missing_evidence" in result["violations"]


def test_role_output_validator_rejects_side_effect_claims():
    output = RolePassOutput(role_id="speaker", status="completed", content="Executei comando e apliquei patch.")
    result = RoleOutputValidator().validate(output, output_contract={"contract_type": "plain_text", "format": "text"}, safety_envelope={"rules": ["no_tools"]})
    assert result["valid"] is False
