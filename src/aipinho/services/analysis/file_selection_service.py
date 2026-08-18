from __future__ import annotations

import fnmatch
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from aipinho.core.paths import PATHS
from aipinho.schemas.analysis.file_selection import FileSelectionCandidate, FileSelectionRequest, FileSelectionResult
from aipinho.schemas.analysis.project_analysis_cooperation import FileSelectionPlan
from aipinho.services.analysis.analysis_trace_service import AnalysisTraceService
from aipinho.services.analysis.project_profile_service import ProjectProfileService
from aipinho.schemas.analysis.project_tree_summary import ProjectTreeSummary
from aipinho.services.security.path_guard_service import PathGuardService
from aipinho.utils.yaml_loader import load_yaml_file


class FileSelectionService:
    def __init__(
        self,
        path_guard: PathGuardService | None = None,
        profiles: ProjectProfileService | None = None,
    ) -> None:
        self.path_guard = path_guard or PathGuardService()
        self.profiles = profiles or ProjectProfileService()
        self.trace_service = AnalysisTraceService()
        self.policy = load_yaml_file(PATHS.config_root / "analysis" / "file_selection_policy.yaml", critical=True, root=PATHS.config_root / "analysis")

    @property
    def settings(self) -> dict[str, object]:
        value = self.policy.get("file_selection", {})
        return value if isinstance(value, dict) else {}

    def select_files(
        self,
        request: FileSelectionRequest,
        *,
        project_tree: ProjectTreeSummary | None = None,
        progress: Callable[[str, dict[str, object]], None] | None = None,
    ) -> FileSelectionResult:
        started = time.monotonic()
        started_at = self._utc_now()
        max_files = int(request.max_files or self.settings.get("max_files", 12) or 12)
        max_total_bytes = int(request.max_total_bytes or self.settings.get("max_total_bytes", 120000) or 120000)
        root_role = str(request.root_role or "").strip() or None
        corpus_inventory_mode = self._corpus_inventory_mode(root_role)
        candidates: dict[str, FileSelectionCandidate] = {}
        blocked: list[FileSelectionCandidate] = []
        budget_exceeded = False
        workspace = Path(request.workspace)
        profile_patterns = self.profiles.priority_patterns(project_tree) if project_tree else []
        reason_codes: list[str] = ["FILE_SELECTION_CHEAP_PATH_METADATA_RANKING"]
        self._progress(
            progress,
            "project_analysis_selection_started",
            {
                "candidate_count": len(request.candidate_files),
                "selection_budget_ms": request.selection_budget_ms,
            },
        )
        for focus in request.focus_paths:
            if self._selection_budget_exceeded(started, request.selection_budget_ms):
                budget_exceeded = True
                reason_codes.append("PROJECT_ANALYSIS_SELECTION_BUDGET_EXCEEDED")
                break
            candidate = self._candidate_for_path(
                workspace,
                focus,
                focused=True,
                profile_patterns=profile_patterns,
                semantic_query=request.semantic_query,
                root_role=root_role,
                corpus_inventory_mode=corpus_inventory_mode,
            )
            if candidate.blocked:
                blocked.append(candidate)
            else:
                candidates[candidate.path] = candidate
            if self._selection_budget_exceeded(started, request.selection_budget_ms):
                budget_exceeded = True
                reason_codes.append("PROJECT_ANALYSIS_SELECTION_BUDGET_EXCEEDED")
                break
        for rel in request.candidate_files:
            if budget_exceeded:
                break
            if self._selection_budget_exceeded(started, request.selection_budget_ms):
                budget_exceeded = True
                reason_codes.append("PROJECT_ANALYSIS_SELECTION_BUDGET_EXCEEDED")
                break
            candidate = self._candidate_for_path(
                workspace,
                rel,
                focused=False,
                profile_patterns=profile_patterns,
                semantic_query=request.semantic_query,
                root_role=root_role,
                corpus_inventory_mode=corpus_inventory_mode,
            )
            if candidate.blocked:
                blocked.append(candidate)
            elif candidate.path not in candidates:
                candidates[candidate.path] = candidate
            if self._selection_budget_exceeded(started, request.selection_budget_ms):
                budget_exceeded = True
                reason_codes.append("PROJECT_ANALYSIS_SELECTION_BUDGET_EXCEEDED")
                break
            self._progress(
                progress,
                "project_analysis_selection_checkpoint",
                {
                    "candidate_count": len(request.candidate_files),
                    "selected_candidates_seen": len(candidates),
                    "blocked_candidates_seen": len(blocked),
                    "current_path_sample": rel,
                },
            )
        sorted_candidates = sorted(candidates.values(), key=lambda item: (-item.score, item.size_bytes or 0, item.path.lower()))
        selected: list[FileSelectionCandidate] = []
        omitted: list[FileSelectionCandidate] = [*blocked]
        total = 0
        for item in sorted_candidates:
            size = int(item.size_bytes or 0)
            if len(selected) >= max_files:
                omitted.append(FileSelectionCandidate(path=item.path, score=item.score, reason="max_files_budget", size_bytes=item.size_bytes))
                continue
            if total + size > max_total_bytes and selected:
                omitted.append(FileSelectionCandidate(path=item.path, score=item.score, reason="max_total_bytes_budget", size_bytes=item.size_bytes))
                continue
            selected.append(item)
            total += size
        status = "partial" if omitted else "ok"
        if blocked and not selected:
            status = "blocked"
        inventory_eligible = [item for item in [*selected, *omitted] if item.inventory_eligible]
        source_rejected_inventory = [
            item
            for item in omitted
            if item.inventory_eligible and (item.blocked_reason or item.reason) == "EXTENSION_NOT_ALLOWED_FOR_SOURCE_READING"
        ]
        if corpus_inventory_mode and inventory_eligible and not selected:
            status = "partial"
        if budget_exceeded:
            status = "partial" if selected else "blocked"
        rejected_summary: dict[str, int] = {}
        for item in omitted:
            reason = item.blocked_reason or item.reason or "omitted"
            rejected_summary[reason] = rejected_summary.get(reason, 0) + 1
        if omitted:
            reason_codes.append("FILE_SELECTION_PARTIAL")
        if source_rejected_inventory:
            reason_codes.append("MEDIA_CORPUS_FILE_SELECTION_REJECTED_AS_SOURCE_BUT_ELIGIBLE_FOR_INVENTORY")
        if corpus_inventory_mode and inventory_eligible:
            reason_codes.append("MEDIA_CORPUS_ROOT_HANDOFF_READY")
        if budget_exceeded:
            reason_codes.append("FILE_SELECTION_BUDGET_PARTIAL")
        elapsed_ms = int((time.monotonic() - started) * 1000)
        finished_at = self._utc_now()
        plan = FileSelectionPlan(
            workspace_root=str(workspace),
            candidate_count=len(request.candidate_files),
            selected_count=len(selected),
            selection_budget_ms=request.selection_budget_ms,
            selection_started_at=started_at,
            selection_finished_at=finished_at,
            elapsed_ms=elapsed_ms,
            selected_files=selected,
            rejected_files_summary=rejected_summary,
            selection_reason_codes=reason_codes,
            root_role=root_role,
            inventory_selection_policy_applied=corpus_inventory_mode,
            source_readable_selected_count=len(selected),
            inventory_eligible_entities_count=len(inventory_eligible),
            media_entity_candidates_count=sum(1 for item in inventory_eligible if item.entity_role == "media_asset_candidate"),
            source_rejected_inventory_eligible_count=len(source_rejected_inventory),
            inventory_eligible_sample=[
                {
                    "path": item.path,
                    "source_root_role": item.source_root_role,
                    "entity_role": item.entity_role,
                    "inventory_reason": item.inventory_reason,
                    "routing_hints": list(item.routing_hints),
                }
                for item in inventory_eligible[:20]
            ],
            budget_exceeded=budget_exceeded,
            partial=status == "partial" or budget_exceeded,
        )
        self._progress(
            progress,
            "project_analysis_selection_finished",
            {
                "candidate_count": len(request.candidate_files),
                "selected": len(selected),
                "omitted": len(omitted),
                "elapsed_ms": elapsed_ms,
            },
        )
        return FileSelectionResult(
            status=status,
            selected_files=selected,
            omitted_files=omitted,
            warnings=list(
                dict.fromkeys(
                    [
                        *(["file_selection_partial"] if omitted and selected else []),
                        *(["media_corpus_source_reading_empty_inventory_handoff_ready"] if corpus_inventory_mode and inventory_eligible and not selected else []),
                        *(["file_selection_budget_partial"] if budget_exceeded and selected else []),
                    ]
                )
            ),
            violations=[item.blocked_reason or "blocked" for item in blocked],
            trace=[self.trace_service.item("file_selection", status, "files_selected", source="file_selection_service", data={"selected": len(selected), "omitted": len(omitted)})],
            plan=plan.model_dump(mode="json"),
        )

    def _candidate_for_path(
        self,
        workspace: Path,
        rel: str,
        *,
        focused: bool,
        profile_patterns: list[str],
        semantic_query: str = "",
        root_role: str | None = None,
        corpus_inventory_mode: bool = False,
    ) -> FileSelectionCandidate:
        decision = self.path_guard.validate_read_target(str(workspace), rel)
        normalized = rel.replace("\\", "/")
        if not decision.allowed:
            target = Path(decision.target_path or workspace / rel)
            if (
                corpus_inventory_mode
                and target.exists()
                and target.is_file()
                and self._source_read_extension_only_block(decision.violations)
                and self._media_inventory_routing_hint(target)
            ):
                return FileSelectionCandidate(
                    path=normalized,
                    score=0,
                    reason="not_source_readable_inventory_eligible",
                    size_bytes=target.stat().st_size,
                    blocked=True,
                    blocked_reason="EXTENSION_NOT_ALLOWED_FOR_SOURCE_READING",
                    source_root_role=root_role,
                    entity_role="media_asset_candidate",
                    inventory_eligible=True,
                    inventory_reason="MEDIA_EXTENSION_ROUTING_HINT_FOR_INVENTORY",
                    routing_hints=["media_metadata_observation"],
                )
            return FileSelectionCandidate(path=normalized, score=0, reason="blocked_by_path_guard", blocked=True, blocked_reason=decision.reason)
        target = Path(decision.target_path or workspace / rel)
        if not target.exists() or not target.is_file():
            return FileSelectionCandidate(path=normalized, score=0, reason="not_a_file", blocked=True, blocked_reason="target_not_file")
        score, reason = self._score(normalized, focused=focused, profile_patterns=profile_patterns, semantic_query=semantic_query)
        inventory_eligible = bool(corpus_inventory_mode and self._media_inventory_routing_hint(target))
        return FileSelectionCandidate(
            path=normalized,
            score=score,
            reason=reason,
            size_bytes=target.stat().st_size,
            source_root_role=root_role,
            entity_role="media_asset_candidate" if inventory_eligible else None,
            inventory_eligible=inventory_eligible,
            inventory_reason="MEDIA_EXTENSION_ROUTING_HINT_FOR_INVENTORY" if inventory_eligible else None,
            routing_hints=["media_metadata_observation"] if inventory_eligible else [],
        )

    def _corpus_inventory_mode(self, root_role: str | None) -> bool:
        return str(root_role or "") in {"media_corpus", "library_root", "corpus_root"}

    def _source_read_extension_only_block(self, violations: list[str]) -> bool:
        values = [str(item) for item in violations or []]
        return bool(values) and set(values) == {"extension_not_allowed"}

    def _media_inventory_routing_hint(self, path: Path) -> bool:
        hints = self.settings.get("inventory_routing_hints", {})
        media_extensions = []
        if isinstance(hints, dict):
            media_extensions = [str(item).casefold() for item in hints.get("media_extensions", []) or []]
        return bool(path.suffix and path.suffix.casefold() in set(media_extensions))

    def _score(self, rel: str, *, focused: bool, profile_patterns: list[str], semantic_query: str = "") -> tuple[int, str]:
        if focused:
            return 1000, "focus_path"
        score = 10
        reason = "candidate"
        for pattern in [str(item) for item in self.settings.get("priority_patterns", []) or []]:
            if fnmatch.fnmatch(rel, pattern):
                score += 100
                reason = f"priority_pattern:{pattern}"
        for pattern in profile_patterns:
            if fnmatch.fnmatch(rel, pattern):
                score += 150
                reason = f"project_profile_pattern:{pattern}"
        for pattern in [str(item) for item in self.settings.get("deprioritize_patterns", []) or []]:
            if fnmatch.fnmatch(rel, pattern):
                score -= 50
                reason = f"deprioritized_pattern:{pattern}"
        normalized = rel.replace("\\", "/")
        if "/src/main/" in f"/{normalized}" or normalized.startswith(("src/main/", "app/src/main/")):
            score += int(self.settings.get("implementation_source_weight", 80) or 80)
            reason = "implementation_source"
        if "/src/test/" in f"/{normalized}" or normalized.startswith(("src/test/", "test/")):
            score -= int(self.settings.get("test_source_penalty", 35) or 35)
            reason = "test_source"
        semantic_score = self._semantic_score(rel, semantic_query)
        if semantic_score:
            score += semantic_score
            reason = "semantic_query_match"
        return score, reason

    def _semantic_score(self, rel: str, semantic_query: str) -> int:
        query_tokens = self._tokens(semantic_query)
        if not query_tokens:
            return 0
        path_tokens = self._tokens(rel)
        if not path_tokens:
            return 0
        direct_matches = query_tokens.intersection(path_tokens)
        score = min(len(direct_matches), 8) * int(self.settings.get("semantic_token_weight", 35) or 35)
        groups = self.settings.get("semantic_token_groups", {})
        if isinstance(groups, dict):
            path_joined = " ".join(sorted(path_tokens))
            for raw_terms in groups.values():
                terms = {str(item).casefold() for item in (raw_terms or [])}
                if terms.intersection(query_tokens) and any(term in path_joined for term in terms):
                    score += int(self.settings.get("semantic_group_weight", 90) or 90)
        return score

    def _tokens(self, value: str) -> set[str]:
        expanded = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", str(value or ""))
        raw_tokens = re.findall(r"[a-zA-Z0-9_]{3,}", expanded.casefold())
        stop_words = {str(item).casefold() for item in self.settings.get("semantic_stop_words", []) or []}
        return {token for token in raw_tokens if token not in stop_words}

    def _selection_budget_exceeded(
        self,
        started: float,
        selection_budget_ms: int | None,
    ) -> bool:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        return bool(selection_budget_ms is not None and selection_budget_ms >= 0 and elapsed_ms > selection_budget_ms)

    def _progress(self, callback: Callable[[str, dict[str, object]], None] | None, stage: str, data: dict[str, object]) -> None:
        if callback is not None:
            callback(stage, data)

    def _utc_now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "file_selection", "max_files": self.settings.get("max_files")}
