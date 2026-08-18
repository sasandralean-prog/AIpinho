from __future__ import annotations

from aipinho.schemas.patching.quality.diff_parse_result import DiffParseResult
from aipinho.schemas.patching.quality.hunk_validation_result import HunkValidationResult
from aipinho.schemas.patching.quality.patch_quality_finding import PatchQualityFinding


class HunkConsistencyValidator:
    def validate(self, parse: DiffParseResult, file_contents: dict[str, str]) -> HunkValidationResult:
        findings: list[PatchQualityFinding] = []
        matching = 0
        for hunk_index, hunk in enumerate(parse.hunks, start=1):
            content = self._lookup_content(hunk.file_path, file_contents)
            if content is None:
                if self._is_new_file_hunk(hunk):
                    matching += 1
                    continue
                findings.append(PatchQualityFinding(finding_id=f"hunk_missing_content_{hunk_index}", category="hunk_validation", severity="high", message="Nao ha snapshot do arquivo para validar hunk.", file_path=hunk.file_path, blocking=True))
                continue
            for line_index, removed in enumerate(hunk.removed_lines, start=1):
                if removed and removed not in content:
                    findings.append(PatchQualityFinding(finding_id=f"hunk_removed_line_{hunk_index}_{line_index}", category="hunk_validation", severity="critical", message="Linha removida pelo diff nao existe no snapshot atual.", file_path=hunk.file_path, blocking=True))
                else:
                    matching += 1
        valid = not any(item.blocking for item in findings)
        return HunkValidationResult(status="ok" if valid else "failed", valid=valid, checked_hunks=len(parse.hunks), matching_removed_lines=matching, findings=findings)

    def _lookup_content(self, file_path: str, file_contents: dict[str, str]) -> str | None:
        normalized = file_path.replace("\\", "/")
        for key, value in file_contents.items():
            key_normalized = key.replace("\\", "/")
            if key_normalized == normalized or key_normalized.endswith("/" + normalized):
                return value
        return None

    def _is_new_file_hunk(self, hunk) -> bool:
        return hunk.old_count == 0 and not hunk.removed_lines and bool(hunk.added_lines)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "hunk_consistency_validator", "execution_enabled": False}
