from aipinho.services.artifacts.artifact_format_validator import ArtifactFormatValidator


def test_artifact_format_validator_json_markdown_yaml_html_csv():
    service = ArtifactFormatValidator()
    assert service.detect_format("reports/a.md") == "markdown"
    assert service.validate("# ok", "markdown")[0] is True
    assert service.validate('{"ok": true}', "json")[0] is True
    assert service.validate("{bad", "json")[0] is False
    assert service.validate("name: value", "yaml")[0] is True
    assert service.validate("a,b\n1,2", "csv")[0] is True
    assert service.validate("<script>alert(1)</script>", "html")[0] is False
