from aipinho.services.evaluation.markdown_output_validator import MarkdownOutputValidator


def test_markdown_output_validator_accepts_required_sections():
    content = "## Executive Summary\nA\n## Findings\nB\n## Recommendations\nC\n## Limitations\nD"
    result = MarkdownOutputValidator().validate(content, required_sections=["executive_summary", "findings", "recommendations", "limitations"])
    assert result.valid is True


def test_markdown_output_validator_detects_missing_sections():
    result = MarkdownOutputValidator().validate("# Findings\nB", required_sections=["findings", "limitations"])
    assert result.valid is False
    assert result.missing_sections == ["limitations"]


def test_markdown_output_validator_accepts_heading_styles():
    result = MarkdownOutputValidator().validate("### Limitations\nD", required_sections=["limitations"])
    assert result.valid is True


def test_markdown_output_validator_rejects_empty_content():
    result = MarkdownOutputValidator().validate("", required_sections=["findings"])
    assert "empty_response" in result.violations
