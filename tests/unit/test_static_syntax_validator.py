from aipinho.services.patching.quality.static_syntax_validator import StaticSyntaxValidator


def test_static_syntax_validator_blocks_invalid_python_without_executing():
    result = StaticSyntaxValidator().validate({"src/app.py": "def broken(:\n    pass\n"})
    assert result.valid is False
    assert result.syntax_results[0].parser == "python_ast"
    assert any(finding.category == "syntax" for finding in result.findings)
