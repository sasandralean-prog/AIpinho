from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.utils.yaml_loader import load_yaml_file


@dataclass(frozen=True)
class NoChangeEvidence:
    status: str
    reason_code: str
    report_path: str
    verdict: str
    summary: str
    evidence_refs: list[str]


class TaskNoChangeEvidenceService:
    """Detects when prior diagnostic evidence proves a patch is unnecessary."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or load_yaml_file(
            PATHS.config_root / "runtime" / "task_no_change_policy.yaml",
            critical=True,
            root=PATHS.config_root / "runtime",
        )

    def evaluate(self, *, prompt: str, workspace: str | None) -> NoChangeEvidence | None:
        if not workspace:
            return None
        if not self._prompt_refs_prior_evidence(prompt):
            return None
        root = self._workspace_root(workspace)
        if root is None:
            return None
        for report in self._candidate_reports(root):
            text = self._read_report(report)
            if not text:
                continue
            if self._excluded_report_status(text):
                continue
            verdict = self._extract_verdict(text)
            if not verdict or not self._positive_verdict(verdict):
                continue
            relative = report.relative_to(root).as_posix()
            return NoChangeEvidence(
                status="no_changes_needed",
                reason_code="prior_diagnostic_indicates_no_patch_needed",
                report_path=relative,
                verdict=verdict,
                summary=self._summary(text, verdict),
                evidence_refs=[f"file:{relative}", f"verdict:{verdict}"],
            )
        return None

    def _prompt_refs_prior_evidence(self, prompt: str) -> bool:
        lowered = self._normalize(prompt)
        evidence = self.config.get("evidence", {})
        refs = [self._normalize(str(item)) for item in evidence.get("prompt_reference_terms", []) or []]
        requests = [self._normalize(str(item)) for item in evidence.get("completion_request_terms", []) or []]
        return any(term and term in lowered for term in refs) and any(term and term in lowered for term in requests)

    def _workspace_root(self, workspace: str) -> Path | None:
        try:
            root = Path(workspace).resolve()
        except Exception:
            return None
        if not root.exists() or not root.is_dir():
            return None
        return root

    def _candidate_reports(self, root: Path) -> list[Path]:
        evidence = self.config.get("evidence", {})
        report_dirs = [str(item) for item in evidence.get("report_dirs", []) or []]
        max_reports = int(evidence.get("max_reports", 12))
        reports: list[Path] = []
        for report_dir in report_dirs:
            base = root / report_dir
            if not base.exists() or not base.is_dir():
                continue
            reports.extend(path for path in base.rglob("*.md") if path.is_file())
            reports.extend(path for path in base.rglob("*.txt") if path.is_file())
        reports.sort(key=lambda item: item.stat().st_mtime, reverse=True)
        return reports[:max_reports]

    def _read_report(self, path: Path) -> str:
        max_bytes = int(self.config.get("evidence", {}).get("max_bytes_per_report", 200000))
        try:
            return path.read_bytes()[:max_bytes].decode("utf-8", errors="replace")
        except OSError:
            return ""

    def _extract_verdict(self, text: str) -> str | None:
        return self._extract_section_value(text, {"veredito", "verdict"})

    def _excluded_report_status(self, text: str) -> bool:
        status = self._extract_section_value(text, {"status"})
        excluded = {
            self._normalize(str(item))
            for item in self.config.get("evidence", {}).get("excluded_report_statuses", []) or []
        }
        return bool(status and self._normalize(status) in excluded)

    def _extract_section_value(self, text: str, headings: set[str]) -> str | None:
        lines = text.splitlines()
        for index, line in enumerate(lines):
            normalized_line = self._normalize(line).strip(": ")
            if normalized_line in headings:
                for next_line in lines[index + 1:index + 4]:
                    value = self._clean_verdict(next_line)
                    if value:
                        return value
            for heading in headings:
                match = re.search(rf"\b{re.escape(heading)}\b\s*[:=-]\s*(.+)$", normalized_line)
                if match:
                    value = self._clean_verdict(match.group(1))
                    if value:
                        return value
        return None

    def _clean_verdict(self, value: str) -> str | None:
        clean = re.sub(r"\s+", " ", value).strip(" -*`\"'.:;")
        if not clean:
            return None
        token = clean.split()[0].strip(" -*`\"'.:;")
        return token.casefold() if token else None

    def _positive_verdict(self, verdict: str) -> bool:
        evidence = self.config.get("evidence", {})
        positives = {self._normalize(str(item)) for item in evidence.get("positive_verdicts", []) or []}
        negatives = [self._normalize(str(item)) for item in evidence.get("negative_verdict_fragments", []) or []]
        normalized = self._normalize(verdict)
        if any(fragment and fragment in normalized for fragment in negatives):
            return False
        return normalized in positives

    def _summary(self, text: str, verdict: str) -> str:
        lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
        lines = [line for line in lines if line]
        preview = " ".join(lines[:8])
        if len(preview) > 800:
            preview = preview[:797] + "..."
        return f"Diagnostico anterior com veredito {verdict}: {preview}"

    def _normalize(self, value: str) -> str:
        return (
            value.casefold()
            .replace("ç", "c")
            .replace("ã", "a")
            .replace("á", "a")
            .replace("à", "a")
            .replace("â", "a")
            .replace("é", "e")
            .replace("ê", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("ô", "o")
            .replace("ú", "u")
        )

    def status(self) -> dict[str, object]:
        evidence = self.config.get("evidence", {})
        return {
            "status": "ok",
            "service": "task_no_change_evidence",
            "positive_verdicts": len(evidence.get("positive_verdicts", []) or []),
        }
