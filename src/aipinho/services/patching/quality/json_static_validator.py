from __future__ import annotations

import json

from aipinho.schemas.patching.quality.patch_quality_finding import PatchQualityFinding
from aipinho.schemas.patching.quality.syntax_validation_result import SyntaxValidationResult


class JsonStaticValidator:
    def validate(self, file_path: str, content: str) -> SyntaxValidationResult:
        findings: list[PatchQualityFinding] = []
        try:
            json.loads(content or "{}")
        except json.JSONDecodeError as exc:
            findings.append(PatchQualityFinding(finding_id="json_syntax_1", category="syntax", severity="critical", message=f"JSON invalido: {exc.msg}", file_path=file_path, line=exc.lineno, blocking=True))
        valid = not any(item.blocking for item in findings)
        return SyntaxValidationResult(status="ok" if valid else "failed", valid=valid, parser="json", file_path=file_path, findings=findings)
