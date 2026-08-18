from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Callable

from aipinho.core.paths import PATHS
from aipinho.schemas.analysis.project_analysis_request import ProjectAnalysisRequest
from aipinho.schemas.analysis.project_tree_summary import ProjectTreeSummary
from aipinho.services.analysis.analysis_trace_service import AnalysisTraceService
from aipinho.services.security.path_guard_service import PathGuardService
from aipinho.utils.yaml_loader import load_yaml_file


class ProjectTreeService:
    def __init__(self, path_guard: PathGuardService | None = None) -> None:
        self.path_guard = path_guard or PathGuardService()
        self.trace_service = AnalysisTraceService()
        self.tree_policy = load_yaml_file(PATHS.config_root / "analysis" / "project_tree_policy.yaml", critical=True, root=PATHS.config_root / "analysis")
        self.ignore_policy = load_yaml_file(PATHS.config_root / "analysis" / "ignore_patterns.yaml", critical=True, root=PATHS.config_root / "analysis")
        self.file_context_policy = load_yaml_file(PATHS.config_root / "analysis" / "file_context_policy.yaml", critical=True, root=PATHS.config_root / "analysis")

    @property
    def settings(self) -> dict[str, object]:
        value = self.tree_policy.get("project_tree", {})
        return value if isinstance(value, dict) else {}

    def build_tree_summary(
        self,
        request: ProjectAnalysisRequest,
        *,
        progress: Callable[[str, dict[str, object]], None] | None = None,
    ) -> ProjectTreeSummary:
        self._progress(progress, "before_path_resolution", {"workspace": request.workspace})
        decision = self.path_guard.validate_read_target(request.workspace, ".")
        self._progress(
            progress,
            "after_path_resolution",
            {"workspace": request.workspace, "resolved_path": decision.target_path or request.workspace},
        )
        if not decision.allowed:
            return ProjectTreeSummary(
                workspace=request.workspace,
                status="blocked" if decision.status == "blocked" else "invalid",
                violations=list(decision.violations),
                warnings=list(decision.warnings),
                trace=[*self.trace_service.from_raw(decision.trace), self.trace_service.item("project_tree", "blocked", decision.reason, source="project_tree_service")],
            )
        root = Path(decision.target_path or request.workspace)
        self._progress(progress, "before_workspace_root_scan", {"current_root": str(root)})
        max_depth = int(self.settings.get("max_depth", 4) or 4)
        max_entries = int(self.settings.get("max_entries", 500) or 500)
        max_candidate_files = int(self.settings.get("max_candidate_files", 200) or 200)
        include_hidden = bool(self.settings.get("include_hidden", False))
        follow_symlinks = bool(self.settings.get("follow_symlinks", False))
        important_names = [str(item) for item in self.settings.get("important_names", []) or []]
        top_level: list[str] = []
        important_paths: list[str] = []
        candidate_files: list[str] = []
        ignored_paths: list[str] = []
        blocked_paths: list[str] = []
        warnings: list[str] = []
        dirs_seen = 0
        files_seen = 0
        entries_seen = 0
        if not root.exists() or not root.is_dir():
            self._progress(progress, "after_workspace_root_scan", {"current_root": str(root), "status": "invalid"})
            return ProjectTreeSummary(workspace=str(root), status="invalid", root_name=root.name, violations=["workspace_not_directory"], trace=[self.trace_service.item("project_tree", "invalid", "workspace_not_directory", source="project_tree_service")])
        self._progress(progress, "after_workspace_root_scan", {"current_root": str(root), "status": "ok"})
        self._progress(progress, "before_file_enumeration", {"current_root": str(root)})
        try:
            for child in sorted(root.iterdir(), key=lambda item: item.name.lower()):
                top_level.append(child.name)
        except OSError as exc:
            return ProjectTreeSummary(workspace=str(root), status="degraded", root_name=root.name, warnings=[str(exc)], trace=[self.trace_service.item("project_tree", "degraded", "top_level_scan_failed", source="project_tree_service")])
        stack: list[tuple[Path, int]] = [(root, 0)]
        while stack:
            current, depth = stack.pop()
            self._progress(
                progress,
                "during_file_enumeration",
                {
                    "current_root": str(root),
                    "current_path_sample": self._rel(current, root),
                    "files_scan_attempted": entries_seen,
                    "files_scanned": files_seen,
                    "files_discovered": len(candidate_files),
                },
            )
            if entries_seen >= max_entries:
                warnings.append("project_tree_entries_truncated")
                break
            if depth > max_depth:
                continue
            try:
                children = sorted(current.iterdir(), key=lambda item: item.name.lower())
            except OSError as exc:
                ignored_paths.append(self._rel(current, root))
                warnings.append(f"scan_failed:{self._rel(current, root)}:{exc}")
                continue
            for child in children:
                rel = self._rel(child, root)
                if entries_seen >= max_entries:
                    warnings.append("project_tree_entries_truncated")
                    break
                entries_seen += 1
                if entries_seen % max(1, int(self.settings.get("progress_poll_interval", 50) or 50)) == 0:
                    self._progress(
                        progress,
                        "during_file_enumeration",
                        {
                            "current_root": str(root),
                            "current_path_sample": rel,
                            "files_scan_attempted": entries_seen,
                            "files_scanned": files_seen,
                            "files_discovered": len(candidate_files),
                        },
                    )
                if not include_hidden and child.name.startswith("."):
                    ignored_paths.append(rel)
                    continue
                if child.is_symlink() and not follow_symlinks:
                    ignored_paths.append(rel)
                    continue
                if child.is_dir():
                    dirs_seen += 1
                    if self._ignored_dir(child.name):
                        ignored_paths.append(rel)
                        continue
                    if child.name in important_names or rel in important_names:
                        important_paths.append(rel)
                    if depth < max_depth:
                        stack.append((child, depth + 1))
                    continue
                if child.is_file():
                    files_seen += 1
                    if self._ignored_file(child.name) or self.path_guard.is_secret_path(child) or self.path_guard.is_blocked_extension(child) or self._blocked_extension(child):
                        blocked_paths.append(rel) if (self.path_guard.is_secret_path(child) or self.path_guard.is_blocked_extension(child) or self._blocked_extension(child)) else ignored_paths.append(rel)
                        continue
                    if child.name in important_names or rel in important_names or self._matches_important(rel):
                        important_paths.append(rel)
                    if len(candidate_files) < max_candidate_files:
                        candidate_files.append(rel)
        status = "partial" if warnings else "ok"
        self._progress(
            progress,
            "after_file_enumeration",
            {
                "current_root": str(root),
                "files_scan_attempted": entries_seen,
                "files_scanned": files_seen,
                "files_discovered": len(candidate_files),
            },
        )
        return ProjectTreeSummary(
            workspace=str(root),
            status=status,
            root_name=root.name,
            total_files_seen=files_seen,
            total_dirs_seen=dirs_seen,
            top_level=list(dict.fromkeys(top_level)),
            important_paths=list(dict.fromkeys(important_paths)),
            candidate_files=list(dict.fromkeys(candidate_files)),
            ignored_paths=list(dict.fromkeys(ignored_paths)),
            blocked_paths=list(dict.fromkeys(blocked_paths)),
            warnings=list(dict.fromkeys(warnings)),
            trace=[self.trace_service.item("project_tree", status, "tree_summary_built", source="project_tree_service", data={"candidate_files": len(candidate_files)})],
        )

    def _rel(self, path: Path, root: Path) -> str:
        try:
            value = path.relative_to(root)
        except ValueError:
            value = path
        return str(value).replace("\\", "/") or "."

    def _ignored_dir(self, name: str) -> bool:
        dirs = [str(item) for item in (self.ignore_policy.get("ignore_patterns", {}).get("directories", []) if isinstance(self.ignore_policy.get("ignore_patterns", {}), dict) else [])]
        return any(fnmatch.fnmatch(name, pattern) for pattern in dirs)

    def _ignored_file(self, name: str) -> bool:
        files = [str(item) for item in (self.ignore_policy.get("ignore_patterns", {}).get("files", []) if isinstance(self.ignore_policy.get("ignore_patterns", {}), dict) else [])]
        return any(fnmatch.fnmatch(name, pattern) for pattern in files)

    def _blocked_extension(self, path: Path) -> bool:
        context = self.file_context_policy.get("file_context", {}) if isinstance(self.file_context_policy.get("file_context", {}), dict) else {}
        blocked = [str(item).lower() for item in context.get("blocked_extensions", []) or []]
        return path.suffix.lower() in blocked

    def _matches_important(self, rel: str) -> bool:
        return rel in {"src", "tests", "config", "docs"} or rel.startswith(("src/", "tests/", "config/", "docs/"))

    def _progress(self, callback: Callable[[str, dict[str, object]], None] | None, stage: str, data: dict[str, object]) -> None:
        if callback is not None:
            callback(stage, data)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "project_tree", "max_depth": self.settings.get("max_depth"), "max_entries": self.settings.get("max_entries")}
