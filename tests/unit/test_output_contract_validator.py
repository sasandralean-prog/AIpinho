from aipinho.services.evaluation.output_contract_validator import OutputContractValidator


def test_output_contract_validator_accepts_valid_json_contract():
    result = OutputContractValidator().validate('{"findings": [], "limitations": []}', {"contract_type": "json_findings", "format": "json", "required_fields": ["findings", "limitations"]})
    assert result.valid is True
    assert result.format_valid is True


def test_output_contract_validator_rejects_invalid_json_contract():
    result = OutputContractValidator().validate('{"findings":', {"contract_type": "json_findings", "format": "json", "required_fields": ["findings", "limitations"]})
    assert result.valid is False
    assert "invalid_json" in result.violations


def test_output_contract_validator_accepts_markdown_required_sections():
    content = "# Executive Summary\nOk\n# Findings\nNone\n# Recommendations\nContinue\n# Limitations\nStub"
    result = OutputContractValidator().validate(content, {"contract_type": "markdown_report", "format": "markdown", "required_sections": ["executive_summary", "findings", "recommendations", "limitations"]})
    assert result.valid is True


def test_output_contract_validator_rejects_missing_markdown_section():
    content = "# Executive Summary\nOk\n# Findings\nNone\n# Recommendations\nContinue"
    result = OutputContractValidator().validate(content, {"contract_type": "markdown_report", "format": "markdown", "required_sections": ["executive_summary", "findings", "recommendations", "limitations"]})
    assert result.valid is False
    assert "limitations" in result.missing_sections


def test_output_contract_validator_allows_chat_plain_text_fallback():
    result = OutputContractValidator().validate("Resposta humana simples.", {"contract_type": "chat_response", "format": "markdown", "required_sections": ["answer"]})
    assert result.valid is True
    assert result.detected_format == "text"
