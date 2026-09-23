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


def test_json_output_validator_rejects_missing_nested_shape_field():
    result = JSONOutputValidator().validate(
        '{"assessments":[{"limitation_id":"lim_1","impact":"COMPATIBLE","constraints":[]}],"confidence":0.9,"rationale":"ok"}',
        required_fields=["assessments", "confidence", "rationale"],
        json_shape={
            "assessments": {
                "type": "list",
                "item": {
                    "limitation_id": {"type": "string", "enum": ["lim_1"]},
                    "impact": {"type": "string", "enum": ["COMPATIBLE"]},
                    "constraints": "list[string]",
                    "rationale": "non_empty_string",
                },
                "required_count": 1,
            },
            "confidence": "number_between_0_and_1",
            "rationale": "non_empty_string",
        },
    )

    assert result.valid is False
    assert "missing_required_field:assessments[0].rationale" in result.violations


def test_json_output_validator_rejects_nested_enum_mismatch():
    result = JSONOutputValidator().validate(
        '{"assessments":[{"limitation_id":"wrong"}]}',
        required_fields=["assessments"],
        json_shape={
            "assessments": {
                "type": "list",
                "item": {
                    "limitation_id": {"type": "string", "enum": ["lim_1"]},
                },
                "required_count": 1,
            }
        },
    )

    assert result.valid is False
    assert "schema_enum_mismatch:assessments[0].limitation_id" in result.violations



def test_json_output_validator_rejects_empty_declared_enum() -> None:
    result = JSONOutputValidator().validate(
        '{"uses":["invented_use"]}',
        required_fields=["uses"],
        json_shape={
            "uses": {
                "type": "list",
                "item": {"type": "string", "enum": []},
            }
        },
    )

    assert result.valid is False
    assert "schema_enum_mismatch:uses[0]" in result.violations


def test_json_output_validator_rejects_string_pattern_mismatch() -> None:
    result = JSONOutputValidator().validate(
        '{"constraints":["invented prose"]}',
        required_fields=["constraints"],
        json_shape={
            "constraints": {
                "type": "list",
                "item": {
                    "type": "string",
                    "pattern": "^(require_|preserve_)[a-z0-9_]*$",
                },
            }
        },
    )

    assert result.valid is False
    assert "schema_pattern_mismatch:constraints[0]" in result.violations


def test_json_output_validator_reports_empty_string_constraint() -> None:
    result = JSONOutputValidator().validate(
        '{"rationale":""}',
        required_fields=["rationale"],
        json_shape={
            "rationale": {
                "type": "string",
                "non_empty": True,
            }
        },
    )

    assert result.valid is False
    assert "schema_non_empty_mismatch:rationale" in result.violations


def test_json_output_validator_can_reject_trailing_text():
    result = JSONOutputValidator().validate('```json\n{"ok": true}\n```\nextra', reject_trailing_text=True)
    assert "trailing_text_after_json" in result.violations
