from __future__ import annotations

import re

from aipinho.schemas.patching.quality.diff_parse_result import DiffParseResult, ParsedDiffHunk
from aipinho.schemas.patching.quality.patch_quality_finding import PatchQualityFinding


class UnifiedDiffParser:
    HUNK_RE = re.compile(r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? \+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@")

    def parse(self, diff_text: str) -> DiffParseResult:
        findings: list[PatchQualityFinding] = []
        if not diff_text.strip():
            return DiffParseResult(
                status="failed",
                valid=False,
                findings=[self._finding("empty_diff", "error", "Diff vazio nao pode passar no quality gate.", blocking=True)],
            )
        lines = diff_text.splitlines()
        affected_files: list[str] = []
        hunks: list[ParsedDiffHunk] = []
        current_file: str | None = None
        current_hunk: ParsedDiffHunk | None = None
        binary_detected = any("GIT binary patch" in line or line.startswith("Binary files ") for line in lines)
        rename_detected = any(line.startswith("rename from ") or line.startswith("rename to ") for line in lines)
        delete_detected = any(line.startswith("deleted file mode") for line in lines)
        if binary_detected:
            findings.append(self._finding("binary_diff", "critical", "Diff binario nao e validavel estaticamente.", blocking=True))
        if rename_detected:
            findings.append(self._finding("rename_diff", "high", "Rename em diff requer revisao manual explicita.", blocking=True))
        if delete_detected:
            findings.append(self._finding("delete_diff", "high", "Delecao em diff requer revisao manual explicita.", blocking=True))
        for line in lines:
            if line.startswith("+++ "):
                raw = line[4:].strip()
                current_file = self._normalize_file(raw)
                if current_file and current_file != "/dev/null" and current_file not in affected_files:
                    affected_files.append(current_file)
                continue
            match = self.HUNK_RE.match(line)
            if match:
                current_hunk = ParsedDiffHunk(
                    file_path=current_file or "",
                    header=line,
                    old_start=int(match.group("old_start")),
                    old_count=int(match.group("old_count") or "1"),
                    new_start=int(match.group("new_start")),
                    new_count=int(match.group("new_count") or "1"),
                )
                hunks.append(current_hunk)
                continue
            if current_hunk is None:
                continue
            if line.startswith("+") and not line.startswith("+++"):
                current_hunk.added_lines.append(line[1:])
            elif line.startswith("-") and not line.startswith("---"):
                current_hunk.removed_lines.append(line[1:])
            elif line.startswith(" "):
                current_hunk.context_lines.append(line[1:])
        if not affected_files:
            findings.append(self._finding("missing_target", "error", "Diff nao declara arquivo alvo em header +++.", blocking=True))
        if not hunks:
            findings.append(self._finding("missing_hunk", "error", "Diff nao contem hunk unified valido.", blocking=True))
        valid = not any(item.blocking for item in findings)
        return DiffParseResult(
            status="ok" if valid else "failed",
            valid=valid,
            affected_files=affected_files,
            hunks=hunks,
            added_lines=sum(len(item.added_lines) for item in hunks),
            removed_lines=sum(len(item.removed_lines) for item in hunks),
            binary_detected=binary_detected,
            rename_detected=rename_detected,
            delete_detected=delete_detected,
            findings=findings,
        )

    def _normalize_file(self, raw: str) -> str:
        if raw in {"/dev/null", "NUL"}:
            return raw
        if raw.startswith("a/") or raw.startswith("b/"):
            return raw[2:]
        return raw

    def _finding(self, category: str, severity: str, message: str, *, blocking: bool) -> PatchQualityFinding:
        return PatchQualityFinding(finding_id=f"{category}_1", category=category, severity=severity, message=message, blocking=blocking)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "unified_diff_parser", "execution_enabled": False}
