from aipinho.services.evaluation.json_output_validator import JSONOutputValidator


def test_json_output_validator_accepts_valid_json():
    result = JSONOutputValidator().validate('{"findings": [], "limitations": []}', required_fields=["findings", "limitations"])
    assert result.valid is True


def test_json_output_validator_rejects_invalid_json():
    result = JSONOutputValidator().validate('{"findings":', required_fields=["findings"])
    assert "invalid_json" in result.violations


def test_json_output_validator_accepts_markdown_fenced_json():
    result = JSONOutputValidator().validate('```json\n{"findings": [], "limitations": []}\n```', required_fields=["findings", "limitations"])
    assert result.valid is True


def test_json_output_validator_reports_missing_required_fields():
    result = JSONOutputValidator().validate('{"findings": []}', required_fields=["findings", "limitations"])
    assert result.valid is False
    assert "limitations" in result.missing_fields


def test_json_output_validator_can_reject_trailing_text():
    result = JSONOutputValidator().validate('```json\n{"ok": true}\n```\nextra', reject_trailing_text=True)
    assert "trailing_text_after_json" in result.violations
