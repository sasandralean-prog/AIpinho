from __future__ import annotations

import tomllib

from aipinho.schemas.patching.quality.patch_quality_finding import PatchQualityFinding
from aipinho.schemas.patching.quality.syntax_validation_result import SyntaxValidationResult


class TomlStaticValidator:
    def validate(self, file_path: str, content: str) -> SyntaxValidationResult:
        findings: list[PatchQualityFinding] = []
        try:
            tomllib.loads(content or "")
        except tomllib.TOMLDecodeError as exc:
            findings.append(PatchQualityFinding(finding_id="toml_syntax_1", category="syntax", severity="critical", message=f"TOML invalido: {exc}", file_path=file_path, blocking=True))
        valid = not any(item.blocking for item in findings)
        return SyntaxValidationResult(status="ok" if valid else "failed", valid=valid, parser="tomllib", file_path=file_path, findings=findings)
