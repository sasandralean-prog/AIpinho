from __future__ import annotations

import ast

from aipinho.schemas.patching.quality.patch_quality_finding import PatchQualityFinding
from aipinho.schemas.patching.quality.syntax_validation_result import SyntaxValidationResult


class PythonAstValidator:
    RISKY_TERMS = ("eval(", "exec(", "os.system(", "subprocess.")

    def validate(self, file_path: str, content: str) -> SyntaxValidationResult:
        findings: list[PatchQualityFinding] = []
        try:
            ast.parse(content)
        except SyntaxError as exc:
            findings.append(PatchQualityFinding(finding_id="python_syntax_1", category="syntax", severity="critical", message=f"Python invalido: {exc.msg}", file_path=file_path, line=exc.lineno, blocking=True))
        for index, term in enumerate(self.RISKY_TERMS, start=1):
            if term in content:
                findings.append(PatchQualityFinding(finding_id=f"python_risky_term_{index}", category="syntax_risk", severity="high", message=f"Uso de {term} requer revisao de seguranca.", file_path=file_path, blocking=False))
        valid = not any(item.blocking for item in findings)
        return SyntaxValidationResult(status="ok" if valid else "failed", valid=valid, parser="python_ast", file_path=file_path, findings=findings)
