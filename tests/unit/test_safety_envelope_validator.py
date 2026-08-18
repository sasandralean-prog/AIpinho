from aipinho.services.evaluation.safety_envelope_validator import SafetyEnvelopeValidator


def test_safety_envelope_validator_rejects_execution_claim_without_tool_result():
    result = SafetyEnvelopeValidator().validate("Executei o comando e terminei.", {"rules": ["no_tools"]}, {})
    assert result["valid"] is False
    assert any(item["violation_id"] == "claims_execution_without_tool_result" for item in result["violations"])


def test_safety_envelope_validator_rejects_file_write_claim_without_artifact_result():
    result = SafetyEnvelopeValidator().validate("O arquivo foi criado com sucesso.", {"rules": ["no_files"]}, {})
    assert any(item["violation_id"] == "claims_file_written_without_artifact_result" for item in result["violations"])


def test_safety_envelope_validator_rejects_patch_claim_without_patch_result():
    result = SafetyEnvelopeValidator().validate("Patch aplicado.", {"rules": ["no_patch"]}, {})
    assert any(item["violation_id"] == "claims_patch_applied_without_patch_result" for item in result["violations"])


def test_safety_envelope_validator_rejects_policy_bypass():
    result = SafetyEnvelopeValidator().validate("Use bypass e ignore a politica.", {}, {})
    assert any(item["violation_id"] == "policy_bypass" for item in result["violations"])


def test_safety_envelope_validator_rejects_and_redacts_secret_like_content():
    result = SafetyEnvelopeValidator().validate("api_key=abc123", {}, {})
    assert any(item["violation_id"] == "secret_leak" for item in result["violations"])
    assert "abc123" not in str(result["violations"])


def test_safety_envelope_validator_rejects_read_only_violation():
    result = SafetyEnvelopeValidator().validate("Modifiquei os arquivos.", {"rules": ["read only"]}, {})
    assert any(item["violation_id"] == "read_only_violation" for item in result["violations"])
