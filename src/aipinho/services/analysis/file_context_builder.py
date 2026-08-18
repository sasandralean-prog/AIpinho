from __future__ import annotations

import time
from typing import Callable
from uuid import uuid4
from datetime import datetime, timezone

from aipinho.schemas.analysis.file_context_bundle import FileContextBundle
from aipinho.schemas.analysis.file_context_item import FileContextItem
from aipinho.schemas.analysis.file_selection import FileSelectionCandidate, FileSelectionResult
from aipinho.schemas.analysis.project_analysis_cooperation import FileReadPlan
from aipinho.schemas.analysis.project_analysis_request import ProjectAnalysisRequest
from aipinho.schemas.tools.tool_execution import ToolExecutionRequest
from aipinho.services.analysis.analysis_trace_service import AnalysisTraceService
from aipinho.services.analysis.file_context_budget_service import FileContextBudgetService
from aipinho.services.tools.read_only_execution_service import ReadOnlyExecutionService


class FileContextBuilder:
    def __init__(self, execution: ReadOnlyExecutionService | None = None, budget: FileContextBudgetService | None = None) -> None:
        self.execution = execution or ReadOnlyExecutionService()
        self.budget = budget or FileContextBudgetService()
        self.trace_service = AnalysisTraceService()

    def build_context(
        self,
        request: ProjectAnalysisRequest,
        selection: FileSelectionResult,
        *,
        progress: Callable[[str, dict[str, object]], None] | None = None,
    ) -> FileContextBundle:
        read_started = time.monotonic()
        read_started_at = self._utc_now()
        candidates, budget_omitted = self.budget.fit(selection.selected_files, max_files=request.max_files, max_total_bytes=request.max_total_bytes)
        max_total_bytes = int(request.max_total_bytes or self.budget.max_total_bytes(None))
        read_order = [candidate.path for candidate in candidates]
        self._progress(
            progress,
            "project_analysis_file_read_started",
            {
                "selected": len(selection.selected_files),
                "read_candidates": len(candidates),
                "max_files_read": request.max_files or len(candidates),
                "max_bytes_read": max_total_bytes,
                "max_single_file_read_ms": request.max_single_file_read_ms,
            },
        )
        self._progress(
            progress,
            "before_file_read_batch",
            {
                "selected": len(selection.selected_files),
                "files_discovered": len(selection.selected_files),
                "files_read": 0,
                "bytes_read": 0,
            },
        )
        items: list[FileContextItem] = []
        warnings: list[str] = [*selection.warnings]
        violations: list[str] = [*selection.violations]
        total_bytes = 0
        max_file_bytes = self.budget.max_file_bytes(request.max_file_bytes)
        read_decisions: list[dict[str, object]] = []
        partial_read_count = 0
        skipped_count = 0
        bytes_skipped_estimated = 0
        for candidate in candidates:
            remaining_total_bytes = max(0, max_total_bytes - total_bytes)
            remaining_stage_budget_ms = self._remaining_ms(read_started, None)
            single_file_budget_ms = request.max_single_file_read_ms
            file_size = int(candidate.size_bytes or 0)
            decision = self._read_decision(
                candidate,
                file_size=file_size,
                max_file_bytes=max_file_bytes,
                remaining_total_bytes=remaining_total_bytes,
                remaining_stage_budget_ms=remaining_stage_budget_ms,
                remaining_total_budget_ms=None,
                single_file_budget_ms=single_file_budget_ms,
            )
            read_decisions.append(decision)
            if decision["decision"] == "skip":
                skipped_count += 1
                bytes_skipped_estimated += file_size
                omitted_reason = str(decision["reason_code"])
                omitted = FileSelectionCandidate(
                    path=candidate.path,
                    score=candidate.score,
                    reason=omitted_reason,
                    size_bytes=candidate.size_bytes,
                )
                budget_omitted.append(omitted)
                warnings.append(omitted_reason)
                self._progress(
                    progress,
                    "project_analysis_file_skipped_by_budget",
                    {
                        "current_path_sample": candidate.path,
                        "file_size_bytes": file_size,
                        "estimated_read_cost": decision["estimated_read_cost"],
                        "remaining_stage_budget_ms": decision["remaining_stage_budget_ms"],
                        "remaining_total_budget_ms": decision["remaining_total_budget_ms"],
                        "single_file_budget_ms": single_file_budget_ms,
                        "files_read": len(items),
                        "files_skipped": skipped_count,
                        "bytes_read": total_bytes,
                        "reason_code": omitted_reason,
                    },
                )
                continue
            self._progress(
                progress,
                "before_file_read_item",
                {
                    "current_path_sample": candidate.path,
                    "files_discovered": len(selection.selected_files),
                    "files_read": len(items),
                    "bytes_read": total_bytes,
                    "read_decision": decision,
                },
            )
            item_started = time.monotonic()
            result = self.execution.execute(
                ToolExecutionRequest(
                    tool_id="filesystem.read_file",
                    input={"workspace": request.workspace, "path": candidate.path, "max_bytes": int(decision["bytes_requested"])},
                    mode="readonly",
                    include_content=True,
                    include_trace=request.include_trace,
                )
            )
            single_file_elapsed_ms = int((time.monotonic() - item_started) * 1000)
            metadata = dict(result.metadata)
            item_status = "included" if result.status == "executed_readonly" else ("blocked" if result.status == "blocked" else "invalid")
            bytes_read = metadata.get("bytes_read") if isinstance(metadata.get("bytes_read"), int) else None
            total_bytes += int(bytes_read or 0)
            partial_read = bool(decision["decision"] == "partial_read" or metadata.get("truncated") or result.content_truncated)
            if partial_read:
                partial_read_count += 1
                warnings.append("PROJECT_ANALYSIS_FILE_PARTIAL_READ_BY_BUDGET")
            items.append(
                FileContextItem(
                    path=candidate.path,
                    status=item_status,
                    content=result.content,
                    content_truncated=result.content_truncated,
                    size_bytes=metadata.get("size") if isinstance(metadata.get("size"), int) else candidate.size_bytes,
                    bytes_read=bytes_read,
                    extension=metadata.get("extension") if isinstance(metadata.get("extension"), str) else None,
                    execution_id=result.execution_id,
                    warnings=list(dict.fromkeys([*result.warnings, *(["PROJECT_ANALYSIS_FILE_PARTIAL_READ_BY_BUDGET"] if partial_read else [])])),
                    violations=list(result.violations),
                    metadata={
                        **metadata,
                        "read_decision": decision,
                        "partial_read": partial_read,
                        "reason_code": "PROJECT_ANALYSIS_FILE_PARTIAL_READ_BY_BUDGET" if partial_read else "PROJECT_ANALYSIS_FILE_READ_COMPLETED",
                    },
                    trace=self.trace_service.from_raw(result.trace) if request.include_trace else [],
                )
            )
            warnings.extend(result.warnings)
            violations.extend(result.violations)
            self._progress(
                progress,
                "after_file_read_item",
                {
                    "current_path_sample": candidate.path,
                    "files_discovered": len(selection.selected_files),
                    "files_read": len(items),
                    "files_partial_read": partial_read_count,
                    "files_skipped": skipped_count,
                    "bytes_read": total_bytes,
                    "reason_code": "PROJECT_ANALYSIS_FILE_PARTIAL_READ_BY_BUDGET" if partial_read else "PROJECT_ANALYSIS_FILE_READ_COMPLETED",
                    },
            )
            if (
                request.max_single_file_read_ms is not None
                and request.max_single_file_read_ms >= 0
                and single_file_elapsed_ms > request.max_single_file_read_ms
            ):
                warnings.append("PROJECT_ANALYSIS_SINGLE_FILE_READ_BUDGET_OBSERVED_AFTER_BOUNDED_READ")
                self._progress(
                    progress,
                    "project_analysis_file_read_checkpoint",
                    {
                        "current_path_sample": candidate.path,
                        "single_file_elapsed_ms": single_file_elapsed_ms,
                        "max_single_file_read_ms": request.max_single_file_read_ms,
                        "files_read": len(items),
                        "files_partial_read": partial_read_count,
                        "files_skipped": skipped_count,
                        "bytes_read": total_bytes,
                        "reason_code": "PROJECT_ANALYSIS_SINGLE_FILE_READ_BUDGET_OBSERVED_AFTER_BOUNDED_READ",
                    },
                )
        omitted = [*selection.omitted_files, *budget_omitted]
        included = [item for item in items if item.status == "included"]
        if not items and violations:
            status = "blocked"
        elif len(included) != len(items) or omitted or partial_read_count:
            status = "partial"
        else:
            status = "ok"
        self._progress(
            progress,
            "after_file_read_batch",
            {
                "files_discovered": len(selection.selected_files),
                "files_read": len(items),
                "files_partial_read": partial_read_count,
                "files_skipped": skipped_count,
                "bytes_read": total_bytes,
            },
        )
        read_finished_at = self._utc_now()
        skipped_summary = [
            {
                "path": item.path,
                "reason": item.blocked_reason or item.reason,
                "size_bytes": item.size_bytes,
            }
            for item in omitted[:100]
        ]
        read_plan = FileReadPlan(
            selected_files=[candidate.path for candidate in selection.selected_files],
            read_order=read_order,
            max_files_read=int(request.max_files or len(candidates)),
            max_bytes_read=max_total_bytes,
            max_single_file_read_ms=request.max_single_file_read_ms,
            read_started_at=read_started_at,
            read_finished_at=read_finished_at,
            files_read=len(items),
            files_partial_read=partial_read_count,
            files_skipped=skipped_count,
            bytes_read=total_bytes,
            bytes_skipped_estimated=bytes_skipped_estimated,
            read_decisions=read_decisions,
            skipped_files=skipped_summary,
            read_errors=[
                {"path": item.path, "status": item.status, "violations": item.violations}
                for item in items
                if item.status != "included"
            ],
            budget_exceeded=bool(skipped_count or partial_read_count),
            partial=status == "partial" or bool(skipped_count or partial_read_count),
        )
        return FileContextBundle(
            bundle_id=f"file_context_{uuid4().hex}",
            workspace=request.workspace,
            status=status,
            items=items,
            omitted_files=omitted,
            total_bytes_read=total_bytes,
            max_total_bytes=self.budget.max_total_bytes(request.max_total_bytes),
            warnings=list(dict.fromkeys(warnings)),
            violations=list(dict.fromkeys(violations)),
            trace=[self.trace_service.item("file_context", status, "file_context_built", source="file_context_builder", data={"items": len(items), "omitted": len(omitted)})],
            read_plan=read_plan.model_dump(mode="json"),
        )

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "file_context_builder", "budget": self.budget.status(), "execution": self.execution.status()}

    def _progress(self, callback: Callable[[str, dict[str, object]], None] | None, stage: str, data: dict[str, object]) -> None:
        if callback is not None:
            callback(stage, data)

    def _read_decision(
        self,
        candidate: FileSelectionCandidate,
        *,
        file_size: int,
        max_file_bytes: int,
        remaining_total_bytes: int,
        remaining_stage_budget_ms: int | None,
        remaining_total_budget_ms: int | None,
        single_file_budget_ms: int | None,
    ) -> dict[str, object]:
        estimated = self._estimated_read_cost_ms(file_size, max_file_bytes)
        reason_code = "PROJECT_ANALYSIS_FILE_READ_COMPLETED"
        decision = "read"
        bytes_requested = min(max_file_bytes, max(0, remaining_total_bytes))
        minimum_sample_bytes = min(1024, max_file_bytes) if max_file_bytes > 0 else 0
        if bytes_requested <= 0 or (minimum_sample_bytes > 0 and bytes_requested < minimum_sample_bytes):
            decision = "skip"
            reason_code = "PROJECT_ANALYSIS_FILE_SKIPPED_BY_BUDGET"
            bytes_requested = 0
        elif single_file_budget_ms is not None and single_file_budget_ms >= 0 and estimated > single_file_budget_ms:
            if max_file_bytes > 0:
                decision = "partial_read"
                reason_code = "PROJECT_ANALYSIS_FILE_PARTIAL_READ_BY_BUDGET"
                bytes_requested = min(bytes_requested, max(1024, max_file_bytes // 3))
            else:
                decision = "skip"
                reason_code = "PROJECT_ANALYSIS_FILE_SKIPPED_BY_SINGLE_FILE_BUDGET"
                bytes_requested = 0
        elif file_size > max_file_bytes:
            decision = "partial_read"
            reason_code = "PROJECT_ANALYSIS_FILE_PARTIAL_READ_BY_BUDGET"
            bytes_requested = min(bytes_requested, max_file_bytes)
        return {
            "candidate_path": candidate.path,
            "relative_path": candidate.path,
            "file_size_bytes": file_size,
            "estimated_read_cost": estimated,
            "remaining_stage_budget_ms": remaining_stage_budget_ms,
            "remaining_total_budget_ms": remaining_total_budget_ms,
            "remaining_context_bytes": remaining_total_bytes,
            "single_file_budget_ms": single_file_budget_ms,
            "decision": decision,
            "reason_code": reason_code,
            "bytes_requested": int(bytes_requested),
            "provenance": "FileContextBuilder._read_decision",
        }

    def _estimated_read_cost_ms(self, file_size: int, max_file_bytes: int) -> int:
        bounded_size = min(max(0, file_size), max(0, max_file_bytes))
        return max(1, int(bounded_size / 1024))

    def _remaining_ms(self, started: float, max_seconds: float | None) -> int | None:
        if max_seconds is None or max_seconds <= 0:
            return None
        return max(0, int(max_seconds * 1000) - int((time.monotonic() - started) * 1000))

    def _remaining_total_budget_ms(self, total_bytes: int, max_total_bytes: int) -> int | None:
        if max_total_bytes <= 0:
            return None
        return max(0, max_total_bytes - total_bytes)

    def _utc_now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
