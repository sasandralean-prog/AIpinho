from __future__ import annotations

from aipinho.schemas.patching.quality.diff_parse_result import DiffParseResult
from aipinho.schemas.patching.quality.patch_quality_finding import PatchQualityFinding


class DiffScopeValidator:
    def validate(self, parse: DiffParseResult, declared_files: list[str]) -> list[PatchQualityFinding]:
        declared = {item.replace("\\", "/") for item in declared_files}
        findings: list[PatchQualityFinding] = []
        if not declared:
            return findings
        for index, file_path in enumerate(parse.affected_files, start=1):
            normalized = file_path.replace("\\", "/")
            if normalized not in declared and not any(item.endswith(normalized) for item in declared):
                findings.append(PatchQualityFinding(finding_id=f"diff_scope_{index}", category="diff_scope", severity="high", message="Diff altera arquivo fora do escopo declarado do plano.", file_path=file_path, blocking=True))
        return findings

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "diff_scope_validator", "execution_enabled": False}
