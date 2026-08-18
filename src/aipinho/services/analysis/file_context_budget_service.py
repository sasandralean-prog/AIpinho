from __future__ import annotations

from aipinho.core.paths import PATHS
from aipinho.schemas.analysis.file_selection import FileSelectionCandidate
from aipinho.utils.yaml_loader import load_yaml_file


class FileContextBudgetService:
    def __init__(self) -> None:
        self.policy = load_yaml_file(PATHS.config_root / "analysis" / "file_context_policy.yaml", critical=True, root=PATHS.config_root / "analysis")

    @property
    def settings(self) -> dict[str, object]:
        value = self.policy.get("file_context", {})
        return value if isinstance(value, dict) else {}

    def max_files(self, override: int | None = None) -> int:
        return int(override or self.settings.get("max_files", 12) or 12)

    def max_total_bytes(self, override: int | None = None) -> int:
        return int(override or self.settings.get("max_total_bytes", 120000) or 120000)

    def max_file_bytes(self, override: int | None = None) -> int:
        return int(override or self.settings.get("max_file_bytes", 30000) or 30000)

    def fit(self, candidates: list[FileSelectionCandidate], *, max_files: int | None = None, max_total_bytes: int | None = None) -> tuple[list[FileSelectionCandidate], list[FileSelectionCandidate]]:
        selected: list[FileSelectionCandidate] = []
        omitted: list[FileSelectionCandidate] = []
        total = 0
        file_limit = self.max_files(max_files)
        byte_limit = self.max_total_bytes(max_total_bytes)
        for item in candidates:
            size = int(item.size_bytes or 0)
            if len(selected) >= file_limit:
                omitted.append(FileSelectionCandidate(path=item.path, score=item.score, reason="max_files_budget", size_bytes=item.size_bytes))
                continue
            if total + size > byte_limit and selected:
                omitted.append(FileSelectionCandidate(path=item.path, score=item.score, reason="max_total_bytes_budget", size_bytes=item.size_bytes))
                continue
            selected.append(item)
            total += size
        return selected, omitted

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "file_context_budget", "max_files": self.max_files(), "max_total_bytes": self.max_total_bytes()}
