from __future__ import annotations

from aipinho.schemas.patching.quality.diff_parse_result import DiffParseResult
from aipinho.schemas.patching.quality.patch_quality_finding import PatchQualityFinding


class DiffHeaderValidator:
    def validate(self, parse: DiffParseResult) -> list[PatchQualityFinding]:
        findings: list[PatchQualityFinding] = []
        for index, file_path in enumerate(parse.affected_files, start=1):
            if file_path in {"/dev/null", "NUL"}:
                findings.append(PatchQualityFinding(finding_id=f"diff_header_target_{index}", category="diff_header", severity="high", message="Criacao/delecao via /dev/null requer revisao manual.", file_path=file_path, blocking=True))
            if file_path.startswith(("/", "\\")) or ".." in file_path.replace("\\", "/").split("/"):
                findings.append(PatchQualityFinding(finding_id=f"diff_header_path_{index}", category="unsafe_path", severity="critical", message="Header do diff aponta para path absoluto ou escapando raiz.", file_path=file_path, blocking=True))
        return findings

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "diff_header_validator", "execution_enabled": False}
