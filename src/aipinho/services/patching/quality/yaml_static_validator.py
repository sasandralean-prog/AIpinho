from __future__ import annotations

from aipinho.schemas.patching.quality.patch_quality_finding import PatchQualityFinding
from aipinho.schemas.patching.quality.syntax_validation_result import SyntaxValidationResult


class YamlStaticValidator:
    def validate(self, file_path: str, content: str) -> SyntaxValidationResult:
        findings: list[PatchQualityFinding] = []
        try:
            import yaml
            yaml.safe_load(content or "{}")
        except ModuleNotFoundError:
            return SyntaxValidationResult(status="degraded", valid=True, parser="yaml_safe_load_unavailable", file_path=file_path, warnings=["pyyaml_unavailable_static_yaml_check_skipped"])
        except Exception as exc:
            findings.append(PatchQualityFinding(finding_id="yaml_syntax_1", category="syntax", severity="critical", message=f"YAML invalido: {exc}", file_path=file_path, blocking=True))
        valid = not any(item.blocking for item in findings)
        return SyntaxValidationResult(status="ok" if valid else "failed", valid=valid, parser="yaml_safe_load", file_path=file_path, findings=findings)
