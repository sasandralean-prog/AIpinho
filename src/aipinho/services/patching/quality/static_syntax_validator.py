from __future__ import annotations

from aipinho.schemas.patching.quality.static_validation_result import StaticValidationResult
from aipinho.schemas.patching.quality.syntax_validation_result import SyntaxValidationResult
from aipinho.services.patching.quality.json_static_validator import JsonStaticValidator
from aipinho.services.patching.quality.python_ast_validator import PythonAstValidator
from aipinho.services.patching.quality.toml_static_validator import TomlStaticValidator
from aipinho.services.patching.quality.yaml_static_validator import YamlStaticValidator


class StaticSyntaxValidator:
    def __init__(self) -> None:
        self.python = PythonAstValidator()
        self.json = JsonStaticValidator()
        self.yaml = YamlStaticValidator()
        self.toml = TomlStaticValidator()

    def validate(self, proposed_contents: dict[str, str]) -> StaticValidationResult:
        results: list[SyntaxValidationResult] = []
        for file_path, content in proposed_contents.items():
            suffix = file_path.lower().rsplit(".", 1)[-1] if "." in file_path else ""
            if suffix == "py":
                results.append(self.python.validate(file_path, content))
            elif suffix == "json":
                results.append(self.json.validate(file_path, content))
            elif suffix in {"yaml", "yml"}:
                results.append(self.yaml.validate(file_path, content))
            elif suffix == "toml":
                results.append(self.toml.validate(file_path, content))
        findings = [finding for result in results for finding in result.findings]
        warnings = [warning for result in results for warning in result.warnings]
        valid = not any(finding.blocking for finding in findings)
        if not results:
            return StaticValidationResult(status="not_applicable", valid=True, checked_files=0)
        return StaticValidationResult(status="ok" if valid else "failed", valid=valid, checked_files=len(results), syntax_results=results, findings=findings, warnings=warnings)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "static_syntax_validator", "execution_enabled": False}
