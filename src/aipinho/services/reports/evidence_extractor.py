from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid5, NAMESPACE_URL

from aipinho.core.paths import PATHS
from aipinho.schemas.analysis.file_context_bundle import FileContextBundle
from aipinho.schemas.analysis.project_tree_summary import ProjectTreeSummary
from aipinho.schemas.reports.evidence import EvidenceSourceType
from aipinho.schemas.reports.evidence_citation import EvidenceCitation
from aipinho.utils.yaml_loader import load_yaml_file


class EvidenceExtractor:
    def __init__(self) -> None:
        self.policy = load_yaml_file(PATHS.config_root / "reports" / "evidence_policy.yaml", critical=True, root=PATHS.config_root / "reports")

    @property
    def settings(self) -> dict[str, object]:
        value = self.policy.get("evidence", {})
        return value if isinstance(value, dict) else {}

    def extract_from_file_context(self, bundle: FileContextBundle) -> list[EvidenceCitation]:
        citations: list[EvidenceCitation] = []
        for item in bundle.items:
            path = self._normalize_path(item.path)
            if item.status != "included" or item.content is None:
                continue
            if self._is_secret_path(path) or "secret_file" in item.violations:
                continue
            line_start, line_end = self._default_line_range(item.content)
            excerpt = self.create_excerpt(item.content, line_start, line_end)
            citations.append(
                EvidenceCitation(
                    evidence_id=self._id("file", path, excerpt or ""),
                    source_type=self._source_type_for_path(path),
                    path=path,
                    line_start=line_start,
                    line_end=line_end,
                    excerpt=excerpt,
                    hash=self._hash(item.content) if bool(self.settings.get("compute_hash", True)) else None,
                    confidence=0.85,
                    read_audit_event_id=item.metadata.get("audit_event_id") if isinstance(item.metadata.get("audit_event_id"), str) else None,
                    notes=["content_truncated"] if item.content_truncated else [],
                )
            )
        return citations

    def extract_from_tree(self, tree_summary: ProjectTreeSummary) -> list[EvidenceCitation]:
        citations: list[EvidenceCitation] = []
        for path in [*tree_summary.top_level, *tree_summary.important_paths, *tree_summary.candidate_files]:
            normalized = self._normalize_path(path)
            citations.append(
                EvidenceCitation(
                    evidence_id=self._id("tree", normalized, "observed"),
                    source_type="tree",
                    path=normalized,
                    excerpt=f"tree path observed: {normalized}",
                    confidence=0.65,
                    notes=["tree_metadata"],
                )
            )
        for path in [*tree_summary.ignored_paths, *tree_summary.blocked_paths]:
            normalized = self._normalize_path(path)
            citations.append(
                EvidenceCitation(
                    evidence_id=self._id("metadata", normalized, "omitted_or_blocked"),
                    source_type="metadata",
                    path=normalized,
                    excerpt=f"tree path omitted or blocked by policy: {normalized}",
                    confidence=0.55,
                    notes=["no_content_cited"],
                )
            )
        return self._dedupe(citations)

    def extract_absence_evidence(self, pattern: str, tree_summary: ProjectTreeSummary | None = None) -> EvidenceCitation:
        note = "absence checked against project tree" if tree_summary is not None else "absence checked against evidence index"
        return EvidenceCitation(
            evidence_id=self._id("absence", pattern, note),
            source_type="absence",
            path=pattern,
            excerpt=f"no path matched pattern: {pattern}",
            confidence=0.6,
            notes=[note],
        )

    def find_line_ranges(self, content: str, patterns: list[str]) -> list[tuple[int, int]]:
        result: list[tuple[int, int]] = []
        lines = content.splitlines()
        lowered_patterns = [pattern.lower() for pattern in patterns]
        for index, line in enumerate(lines, start=1):
            lowered = line.lower()
            if any(pattern in lowered for pattern in lowered_patterns):
                result.append((index, min(len(lines), index + 4)))
        return result

    def create_excerpt(self, content: str, line_start: int | None, line_end: int | None) -> str:
        if line_start is None or line_end is None:
            excerpt = content[: int(self.settings.get("max_excerpt_chars", 600) or 600)]
        else:
            lines = content.splitlines()
            excerpt = "\n".join(lines[max(0, line_start - 1):line_end])
        max_chars = int(self.settings.get("max_excerpt_chars", 600) or 600)
        return excerpt[:max_chars]

    def _default_line_range(self, content: str) -> tuple[int | None, int | None]:
        lines = content.splitlines()
        if not lines:
            return None, None
        first = 1
        for index, line in enumerate(lines, start=1):
            if line.strip():
                first = index
                break
        return first, min(len(lines), first + 4)

    def _source_type_for_path(self, path: str) -> EvidenceSourceType:
        if path.startswith("config/policies/"):
            return "policy"
        if path.startswith("config/"):
            return "config"
        if path.startswith("tests/"):
            return "test"
        return "file"

    def _is_secret_path(self, path: str) -> bool:
        name = Path(path).name.lower()
        return name == ".env" or name.startswith(".env.") or "secret" in name or "token" in name or "credential" in name

    def _normalize_path(self, path: str) -> str:
        return path.replace(chr(92), "/")

    def _hash(self, value: str) -> str:
        return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()

    def _id(self, source: str, path: str, value: str) -> str:
        return f"evidence_{uuid5(NAMESPACE_URL, source + ':' + path + ':' + value).hex}"

    def _dedupe(self, citations: list[EvidenceCitation]) -> list[EvidenceCitation]:
        seen: set[str] = set()
        result: list[EvidenceCitation] = []
        for item in citations:
            if item.evidence_id in seen:
                continue
            seen.add(item.evidence_id)
            result.append(item)
        return result

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "evidence_extractor", "max_excerpt_chars": self.settings.get("max_excerpt_chars")}
