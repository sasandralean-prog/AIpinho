from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.schemas.analysis.analysis_report import AnalysisReport
from aipinho.schemas.analysis.file_context_bundle import FileContextBundle
from aipinho.schemas.analysis.file_selection import FileSelectionRequest
from aipinho.schemas.analysis.project_analysis_cooperation import (
    ProjectAnalysisBudgetCooperationPolicy,
    ProjectAnalysisPartialReadiness,
)
from aipinho.schemas.analysis.project_analysis_budget import ProjectAnalysisBudget
from aipinho.schemas.analysis.project_analysis_request import ProjectAnalysisRequest
from aipinho.schemas.analysis.project_analysis_result import ProjectAnalysisResult
from aipinho.schemas.analysis.project_tree_summary import ProjectTreeSummary
from aipinho.services.analysis.analysis_report_service import AnalysisReportService
from aipinho.services.analysis.analysis_trace_service import AnalysisTraceService
from aipinho.services.analysis.architecture_analyzer import ArchitectureAnalyzer
from aipinho.services.analysis.dependency_analyzer import DependencyAnalyzer
from aipinho.services.analysis.file_context_builder import FileContextBuilder
from aipinho.services.analysis.file_selection_service import FileSelectionService
from aipinho.services.analysis.functionality_analyzer import FunctionalityAnalyzer
from aipinho.services.analysis.project_structure_detector import ProjectStructureDetector
from aipinho.services.analysis.project_tree_service import ProjectTreeService
from aipinho.utils.yaml_loader import load_yaml_file


class ProjectAnalysisService:
    def __init__(self, tree_service: ProjectTreeService | None = None, selection_service: FileSelectionService | None = None, context_builder: FileContextBuilder | None = None, structure_detector: ProjectStructureDetector | None = None, architecture_analyzer: ArchitectureAnalyzer | None = None, dependency_analyzer: DependencyAnalyzer | None = None, functionality_analyzer: FunctionalityAnalyzer | None = None, report_service: AnalysisReportService | None = None, budget: ProjectAnalysisBudget | None = None) -> None:
        self.tree_service = tree_service or ProjectTreeService()
        self.selection_service = selection_service or FileSelectionService()
        self.context_builder = context_builder or FileContextBuilder()
        self.structure_detector = structure_detector or ProjectStructureDetector()
        self.architecture_analyzer = architecture_analyzer or ArchitectureAnalyzer()
        self.dependency_analyzer = dependency_analyzer or DependencyAnalyzer()
        self.functionality_analyzer = functionality_analyzer or FunctionalityAnalyzer()
        self.report_service = report_service or AnalysisReportService()
        self.trace_service = AnalysisTraceService()
        self.budget = budget or ProjectAnalysisBudget.from_environment()
        self.cooperation_policy = ProjectAnalysisBudgetCooperationPolicy.from_environment(
            max_total_seconds=self.budget.max_total_seconds,
            max_files_scanned=self.budget.max_files_scanned,
            max_files_read=self.budget.max_files_read,
            max_bytes_read=self.budget.max_bytes_read,
            allow_partial_result=self.budget.allow_partial_result,
        )
        self.policy = load_yaml_file(PATHS.config_root / "analysis" / "project_analysis_policy.yaml", critical=True, root=PATHS.config_root / "analysis")

    def analyze_project(self, request: ProjectAnalysisRequest, *, cancel_requested=None) -> ProjectAnalysisResult:
        started = time.monotonic()
        started_at = self._utc_now()
        metrics = self._new_metrics(request)
        tree: ProjectTreeSummary | None = None
        context: FileContextBundle | None = None
        try:
            self._checkpoint(started, "before_path_resolution", cancel_requested=cancel_requested, metrics=metrics)
            tree_request = self._budgeted_request(request)
            tree = self.tree_service.build_tree_summary(
                tree_request,
                progress=lambda stage, data: self._checkpoint(
                    started,
                    stage,
                    cancel_requested=cancel_requested,
                    metrics=metrics,
                    data=data,
                ),
            )
            checkpoint_data = {
                "checkpoint": "after_file_enumeration",
                "files_scan_attempted": max(int(metrics.get("files_scan_attempted") or 0), tree.total_files_seen),
                "files_scanned": tree.total_files_seen,
                "files_discovered": len(tree.candidate_files),
            }
            metrics.update(checkpoint_data)
            if self.budget.max_files_scanned and tree.total_files_seen > self.budget.max_files_scanned:
                return self._blocked_result(
                    request,
                    tree=tree,
                    started=started,
                    started_at=started_at,
                    reason_code="PROJECT_ANALYSIS_FILE_SCAN_BUDGET_EXCEEDED",
                    message="Project analysis scanned more files than the governed budget allows.",
                    metrics=metrics,
                    data=checkpoint_data,
                )
            self._checkpoint(started, "after_file_enumeration", cancel_requested=cancel_requested, metrics=metrics, data=checkpoint_data)
            if tree.status in {"blocked", "invalid"}:
                selection_request = FileSelectionRequest(
                    workspace=request.workspace,
                    goal=request.goal,
                    semantic_query=request.prompt,
                    candidate_files=[],
                    focus_paths=[],
                    selection_budget_ms=int(self.cooperation_policy.max_selection_seconds * 1000),
                )
            else:
                root_role = self._root_role_for_workspace(request, tree.workspace)
                selection_request = FileSelectionRequest(
                    workspace=tree.workspace,
                    goal=request.goal,
                    semantic_query=request.prompt,
                    root_role=root_role,
                    candidate_files=tree.candidate_files,
                    focus_paths=request.focus_paths,
                    max_files=min(self.cooperation_policy.max_files_selected, request.max_files) if request.max_files else self.cooperation_policy.max_files_selected,
                    max_total_bytes=min(self.budget.max_bytes_read, request.max_total_bytes) if request.max_total_bytes else self.budget.max_bytes_read,
                    selection_budget_ms=int(self.cooperation_policy.max_selection_seconds * 1000),
                )
            self._checkpoint(
                started,
                "before_file_selection",
                cancel_requested=cancel_requested,
                metrics=metrics,
                data={"files_discovered": len(tree.candidate_files)},
            )
            selection = self._select_files(
                selection_request,
                tree=tree,
                started=started,
                cancel_requested=cancel_requested,
                metrics=metrics,
            )
            self._checkpoint(
                started,
                "after_file_selection",
                cancel_requested=cancel_requested,
                metrics=metrics,
                data={"selected": len(selection.selected_files), "files_discovered": len(tree.candidate_files)},
            )
            corpus_handoff = self._corpus_handoff_from_selection(request=request, tree=tree, selection=selection)
            if corpus_handoff and corpus_handoff.get("handoff_status") == "ready" and not selection.selected_files:
                return self._corpus_handoff_result(
                    request,
                    tree=tree,
                    selection=selection,
                    corpus_handoff=corpus_handoff,
                    started=started,
                    started_at=started_at,
                    metrics=metrics,
                )
            if corpus_handoff and corpus_handoff.get("handoff_status") == "blocked" and not selection.selected_files:
                return self._blocked_result(
                    request,
                    tree=tree,
                    started=started,
                    started_at=started_at,
                    reason_code=str(corpus_handoff.get("handoff_reason_code") or "PROJECT_ANALYSIS_CORPUS_HANDOFF_FAILED"),
                    message="Project analysis could not create a governed media corpus handoff.",
                    metrics=metrics,
                    data={"checkpoint": "after_file_selection", "corpus_handoff": corpus_handoff, "file_selection_plan": selection.plan or {}},
                )
            if self._selection_plan_budget_exceeded(selection):
                return self._partial_or_blocked_handoff_result(
                    request,
                    tree=tree,
                    context=context,
                    selection=selection,
                    started=started,
                    started_at=started_at,
                    reason_code="PROJECT_ANALYSIS_SELECTION_BUDGET_EXCEEDED",
                    metrics=metrics,
                    data={"checkpoint": "after_file_selection", "file_selection_plan": selection.plan or {}},
                )
            if self._handoff_reserve_reached(started):
                return self._partial_or_blocked_handoff_result(
                    request,
                    tree=tree,
                    context=context,
                    selection=selection,
                    started=started,
                    started_at=started_at,
                    reason_code="PROJECT_ANALYSIS_HANDOFF_RESERVE_REACHED",
                    metrics=metrics,
                    data={"checkpoint": "after_file_selection"},
                )
            context_request = ProjectAnalysisRequest(
                workspace=tree.workspace if tree.status not in {"blocked", "invalid"} else request.workspace,
                prompt=request.prompt,
                goal=request.goal,
                workspace_context=request.workspace_context,
                focus_paths=request.focus_paths,
                max_files=min(self.budget.max_files_read, request.max_files) if request.max_files else self.budget.max_files_read,
                max_total_bytes=min(self.budget.max_bytes_read, request.max_total_bytes) if request.max_total_bytes else self.budget.max_bytes_read,
                max_file_bytes=request.max_file_bytes,
                max_single_file_read_ms=self.cooperation_policy.max_single_file_read_ms,
                include_trace=request.include_trace,
            )
            context = self.context_builder.build_context(
                context_request,
                selection,
                progress=lambda stage, data: self._checkpoint(
                    started,
                    stage,
                    cancel_requested=cancel_requested,
                    metrics=metrics,
                    data=data,
                ),
            )
            read_plan = context.read_plan if isinstance(context.read_plan, dict) else {}
            self._checkpoint(
                started,
                "after_file_read_batch",
                cancel_requested=cancel_requested,
                metrics=metrics,
                data={
                    "files_read": len(context.items),
                    "files_partial_read": int(read_plan.get("files_partial_read") or 0),
                    "files_skipped": int(read_plan.get("files_skipped") or 0),
                    "bytes_read": context.total_bytes_read,
                    "bytes_skipped_estimated": int(read_plan.get("bytes_skipped_estimated") or 0),
                    "read_decisions": list(read_plan.get("read_decisions") or []),
                },
            )
            if self._handoff_reserve_reached(started):
                return self._partial_or_blocked_handoff_result(
                    request,
                    tree=tree,
                    context=context,
                    selection=selection,
                    started=started,
                    started_at=started_at,
                    reason_code="PROJECT_ANALYSIS_HANDOFF_RESERVE_REACHED",
                    metrics=metrics,
                    data={"checkpoint": "after_file_read_batch"},
                )
            if context.total_bytes_read > self.budget.max_bytes_read:
                return self._blocked_result(
                    request,
                    tree=tree,
                    context=context,
                    started=started,
                    started_at=started_at,
                    reason_code="PROJECT_ANALYSIS_FILE_READ_BUDGET_EXCEEDED",
                    message="Project analysis read more bytes than the governed budget allows.",
                    metrics=metrics,
                    data={"bytes_read": context.total_bytes_read},
                )
            self._checkpoint(started, "before_symbol_extraction", cancel_requested=cancel_requested, metrics=metrics)
            structures = self.structure_detector.detect(tree) if tree.status not in {"blocked", "invalid"} else []
            self._checkpoint(started, "after_symbol_extraction_batch", cancel_requested=cancel_requested, metrics=metrics, data={"structures": len(structures)})
            findings = [
                *self.architecture_analyzer.analyze(tree, context, structures),
                *self.dependency_analyzer.analyze(context, tree),
                *self.functionality_analyzer.analyze(context),
            ]
            max_findings = int((self.policy.get("project_analysis", {}) if isinstance(self.policy.get("project_analysis", {}), dict) else {}).get("report_max_findings", 20) or 20)
            findings = findings[:max_findings]
            self._checkpoint(started, "before_result_serialization", cancel_requested=cancel_requested, metrics=metrics, data={"findings": len(findings)})
            report = self.report_service.build_report(request, tree, context, structures, findings)
            self._checkpoint(started, "after_result_serialization", cancel_requested=cancel_requested, metrics=metrics, data={"findings": len(findings)})
            warnings = list(dict.fromkeys([*tree.warnings, *selection.warnings, *context.warnings, *report.warnings]))
            violations = list(dict.fromkeys([*tree.violations, *selection.violations, *context.violations]))
            status = report.status
            metrics.update(
                {
                    "files_discovered": len(tree.candidate_files),
                    "files_scan_attempted": max(int(metrics.get("files_scan_attempted") or 0), tree.total_files_seen),
                    "files_scanned": tree.total_files_seen,
                    "files_read": len(context.items),
                    "files_partial_read": int(read_plan.get("files_partial_read") or 0),
                    "files_skipped": int(read_plan.get("files_skipped") or 0),
                    "bytes_read": context.total_bytes_read,
                    "bytes_skipped_estimated": int(read_plan.get("bytes_skipped_estimated") or 0),
                    "read_decisions": list(read_plan.get("read_decisions") or []),
                }
            )
            result = ProjectAnalysisResult(
                result_id=f"project_analysis_{uuid4().hex}",
                workspace=context.workspace,
                status=status,
                tree_summary=tree,
                file_context=context,
                structures=structures,
                findings=findings,
                report=report,
                warnings=warnings,
                violations=violations,
                trace=[self.trace_service.item("project_analysis", status, "project_analysis_completed", source="project_analysis_service", data={"findings": len(findings), "structures": len(structures)})],
                reason_code="PROJECT_ANALYSIS_COMPLETED" if status in {"ok", "partial"} else "PROJECT_ANALYSIS_DEGRADED",
                started_at=started_at,
                finished_at=self._utc_now(),
                duration_ms=self._duration_ms(started),
                **self._result_metric_fields(metrics),
                files_scanned=tree.total_files_seen,
                files_read=len(context.items),
                bytes_read=context.total_bytes_read,
                findings_count=len(findings),
                dependency_edges_count=0,
                partial=status == "partial",
                budget=self.budget.as_dict(),
                budget_cooperation_policy=self.cooperation_policy.as_dict(),
                file_selection_plan=selection.plan,
                file_read_plan=context.read_plan,
                partial_readiness=self._partial_readiness(tree=tree, selection=selection, context=context).model_dump(mode="json"),
                corpus_handoff=corpus_handoff,
                files_selected=len(selection.selected_files),
                skipped_files_summary=self._skipped_files_summary(selection=selection, context=context),
                elapsed_ms_by_stage=self._elapsed_ms_by_stage(metrics),
                remaining_budget_ms_at_return=self._remaining_budget_ms(started),
                handoff_reserve_reached=False,
                limitations=list(report.limitations),
                safe_to_continue=status in {"ok", "partial", "degraded"},
            )
            if self._encoded_size(result) > self.budget.max_output_bytes:
                return self._blocked_result(
                    request,
                    tree=tree,
                    context=context,
                    started=started,
                    started_at=started_at,
                    reason_code="PROJECT_ANALYSIS_OUTPUT_BUDGET_EXCEEDED",
                    message="Project analysis output exceeded the governed inline output budget.",
                    metrics=metrics,
                    data={"max_output_bytes": self.budget.max_output_bytes},
                )
            return result
        except ProjectAnalysisBudgetExceeded as exc:
            return self._blocked_result(
                request,
                started=started,
                started_at=started_at,
                reason_code=exc.reason_code,
                message=str(exc),
                status="cancelled" if exc.reason_code == "PROJECT_ANALYSIS_CANCELLED" else "timeout",
                cancel_requested=exc.reason_code == "PROJECT_ANALYSIS_CANCELLED",
                tree=tree,
                context=context,
                metrics=metrics,
                data=exc.details,
            )
        except Exception as exc:
            return self._blocked_result(
                request,
                started=started,
                started_at=started_at,
                reason_code="PROJECT_ANALYSIS_BOUNDARY_ERROR",
                message=str(exc) or type(exc).__name__,
                status="failed",
                error_type=type(exc).__name__,
                tree=tree,
                context=context,
                metrics=metrics,
                data={"checkpoint": metrics.get("last_checkpoint")},
            )

    def status(self) -> dict[str, object]:
        components = {
            "project_tree": self.tree_service.status(),
            "file_selection": self.selection_service.status(),
            "file_context": self.context_builder.status(),
            "project_structure": self.structure_detector.status(),
            "architecture": self.architecture_analyzer.status(),
            "dependencies": self.dependency_analyzer.status(),
            "functionality": self.functionality_analyzer.status(),
            "report": self.report_service.status(),
        }
        overall = "ok" if all(item.get("status") == "ok" for item in components.values()) else "degraded"
        return {
            "status": overall,
            "service": "project_analysis",
            "execution_enabled": False,
            "write_enabled": False,
            "budget": self.budget.as_dict(),
            "budget_cooperation_policy": self.cooperation_policy.as_dict(),
            "components": components,
        }

    def _budgeted_request(self, request: ProjectAnalysisRequest) -> ProjectAnalysisRequest:
        return request.model_copy(
            update={
                "max_files": min(self.budget.max_files_read, request.max_files) if request.max_files else self.budget.max_files_read,
                "max_total_bytes": min(self.budget.max_bytes_read, request.max_total_bytes) if request.max_total_bytes else self.budget.max_bytes_read,
                "max_single_file_read_ms": self.cooperation_policy.max_single_file_read_ms,
            }
        )

    def _select_files(
        self,
        request: FileSelectionRequest,
        *,
        tree: ProjectTreeSummary,
        started: float,
        cancel_requested,
        metrics: dict[str, Any],
    ):
        progress = lambda stage, data: self._checkpoint(
            started,
            stage,
            cancel_requested=cancel_requested,
            metrics=metrics,
            data=data,
        )
        try:
            return self.selection_service.select_files(request, project_tree=tree, progress=progress)
        except TypeError as exc:
            if "progress" not in str(exc):
                raise
            return self.selection_service.select_files(request, project_tree=tree)

    def _checkpoint(
        self,
        started: float,
        stage: str,
        *,
        cancel_requested=None,
        metrics: dict[str, Any] | None = None,
        data: dict[str, object] | None = None,
    ) -> None:
        metrics = metrics if metrics is not None else {}
        self._record_checkpoint(started, metrics, stage, data=data)
        if cancel_requested is not None and bool(cancel_requested()):
            raise ProjectAnalysisBudgetExceeded(
                "PROJECT_ANALYSIS_CANCELLED",
                f"Project analysis cancellation checkpoint reached during {stage}.",
                self._budget_details(metrics, stage, data=data),
            )
        if stage == "project_analysis_selection_budget_exceeded":
            raise ProjectAnalysisBudgetExceeded(
                "PROJECT_ANALYSIS_SELECTION_BUDGET_EXCEEDED",
                "Project analysis file selection exceeded its cooperative budget.",
                self._budget_details(metrics, stage, data=data, reason_code="PROJECT_ANALYSIS_SELECTION_BUDGET_EXCEEDED"),
            )
        if stage == "project_analysis_single_file_read_budget_exceeded":
            raise ProjectAnalysisBudgetExceeded(
                "PROJECT_ANALYSIS_SINGLE_FILE_READ_BUDGET_EXCEEDED",
                "Project analysis single file read exceeded its cooperative budget.",
                self._budget_details(metrics, stage, data=data, reason_code="PROJECT_ANALYSIS_SINGLE_FILE_READ_BUDGET_EXCEEDED"),
            )
        if "file_read" in stage and self._stage_elapsed_exceeded(metrics, "_file_read_started_reference", self.cooperation_policy.max_file_read_seconds):
            raise ProjectAnalysisBudgetExceeded(
                "PROJECT_ANALYSIS_FILE_READ_BUDGET_EXCEEDED",
                f"Project analysis file read budget exceeded during {stage}.",
                self._budget_details(metrics, stage, data=data, reason_code="PROJECT_ANALYSIS_FILE_READ_BUDGET_EXCEEDED"),
            )
        elapsed = time.monotonic() - started
        if self.budget.max_total_seconds <= 0 or elapsed > self.budget.max_total_seconds:
            reason_code = self._timeout_reason(stage, metrics)
            raise ProjectAnalysisBudgetExceeded(
                reason_code,
                f"Project analysis budget exceeded during {stage}.",
                self._budget_details(metrics, stage, data=data),
            )

    def _blocked_result(
        self,
        request: ProjectAnalysisRequest,
        *,
        started: float,
        started_at: str,
        reason_code: str,
        message: str,
        tree: ProjectTreeSummary | None = None,
        context: FileContextBundle | None = None,
        status: str = "blocked",
        cancel_requested: bool = False,
        error_type: str | None = None,
        metrics: dict[str, Any] | None = None,
        data: dict[str, object] | None = None,
    ) -> ProjectAnalysisResult:
        metrics = metrics or {}
        tree = tree or ProjectTreeSummary(workspace=request.workspace, status="blocked", warnings=[reason_code])
        context = context or FileContextBundle(bundle_id=f"file_context_{uuid4().hex}", workspace=request.workspace, status="blocked", warnings=[reason_code])
        metric_files_scanned = max(int(metrics.get("files_scanned") or 0), tree.total_files_seen)
        metric_files_read = max(int(metrics.get("files_read") or 0), len(context.items))
        metric_bytes_read = max(int(metrics.get("bytes_read") or 0), context.total_bytes_read)
        read_plan = context.read_plan if isinstance(context.read_plan, dict) else {}
        metric_files_partial_read = max(int(metrics.get("files_partial_read") or 0), int(read_plan.get("files_partial_read") or 0))
        metric_files_skipped = max(int(metrics.get("files_skipped") or 0), int(read_plan.get("files_skipped") or 0))
        metric_bytes_skipped = max(int(metrics.get("bytes_skipped_estimated") or 0), int(read_plan.get("bytes_skipped_estimated") or 0))
        read_decisions = list(metrics.get("read_decisions") or read_plan.get("read_decisions") or [])
        metrics.update(
            {
                "files_scanned": metric_files_scanned,
                "files_read": metric_files_read,
                "files_partial_read": metric_files_partial_read,
                "files_skipped": metric_files_skipped,
                "bytes_read": metric_bytes_read,
                "bytes_skipped_estimated": metric_bytes_skipped,
                "read_decisions": read_decisions,
                "files_discovered": max(int(metrics.get("files_discovered") or 0), len(tree.candidate_files)),
                "files_scan_attempted": max(int(metrics.get("files_scan_attempted") or 0), metric_files_scanned),
            }
        )
        report = AnalysisReport(
            report_id=f"analysis_report_{uuid4().hex}",
            status="blocked" if status in {"blocked", "timeout", "cancelled"} else "degraded",
            title="Project Analysis Boundary",
            summary=message,
            limitations=[reason_code],
            warnings=[reason_code],
        )
        return ProjectAnalysisResult(
            result_id=f"project_analysis_{uuid4().hex}",
            workspace=context.workspace,
            status=status,  # type: ignore[arg-type]
            tree_summary=tree,
            file_context=context,
            report=report,
            warnings=list(dict.fromkeys([*tree.warnings, *context.warnings, reason_code])),
            violations=list(dict.fromkeys([*tree.violations, *context.violations])),
            trace=[self.trace_service.item("project_analysis", status, reason_code, source="project_analysis_service", data=data or {})],
            reason_code=reason_code,
            error_type=error_type,
            error_message=message,
            started_at=started_at,
            finished_at=self._utc_now(),
            duration_ms=self._duration_ms(started),
            **self._result_metric_fields(metrics),
            files_scanned=metric_files_scanned,
            files_read=metric_files_read,
            bytes_read=metric_bytes_read,
            findings_count=0,
            partial=self.budget.allow_partial_result and bool(context.items or tree.candidate_files),
            budget=self.budget.as_dict(),
            budget_cooperation_policy=self.cooperation_policy.as_dict(),
            file_selection_plan=self._selection_plan_from_data(data),
            file_read_plan=context.read_plan,
            partial_readiness=self._partial_readiness(tree=tree, selection=None, context=context).model_dump(mode="json"),
            corpus_handoff=(data or {}).get("corpus_handoff") if isinstance((data or {}).get("corpus_handoff"), dict) else None,
            files_selected=0,
            skipped_files_summary=self._skipped_files_summary(selection=None, context=context),
            elapsed_ms_by_stage=self._elapsed_ms_by_stage(metrics),
            remaining_budget_ms_at_return=self._remaining_budget_ms(started),
            handoff_reserve_reached=reason_code == "PROJECT_ANALYSIS_HANDOFF_RESERVE_REACHED",
            limitations=[reason_code],
            budget_exceeded=reason_code
            in {
                "PROJECT_ANALYSIS_BUDGET_EXCEEDED",
                "PROJECT_ANALYSIS_FILE_SCAN_BUDGET_EXCEEDED",
                "PROJECT_ANALYSIS_FILE_READ_BUDGET_EXCEEDED",
                "PROJECT_ANALYSIS_OUTPUT_BUDGET_EXCEEDED",
                "PROJECT_ANALYSIS_TIMEOUT",
                "PROJECT_ANALYSIS_PATH_RESOLUTION_TIMEOUT",
                "PROJECT_ANALYSIS_ROOT_SCAN_TIMEOUT",
                "PROJECT_ANALYSIS_FILE_ENUMERATION_TIMEOUT",
                "PROJECT_ANALYSIS_FILE_SELECTION_TIMEOUT",
                "PROJECT_ANALYSIS_SELECTION_BUDGET_EXCEEDED",
                "PROJECT_ANALYSIS_FILE_READ_TIMEOUT",
                "PROJECT_ANALYSIS_FILE_READ_BUDGET_EXCEEDED",
                "PROJECT_ANALYSIS_SINGLE_FILE_READ_BUDGET_EXCEEDED",
                "PROJECT_ANALYSIS_SYMBOL_EXTRACTION_TIMEOUT",
                "PROJECT_ANALYSIS_RESULT_SERIALIZATION_TIMEOUT",
                "PROJECT_ANALYSIS_ZERO_PROGRESS_TIMEOUT",
                "PROJECT_ANALYSIS_INSTRUMENTATION_GAP",
            },
            cancel_requested=cancel_requested,
            safe_to_continue=False,
        )

    def _new_metrics(self, request: ProjectAnalysisRequest) -> dict[str, Any]:
        return {
            "_started_reference": time.monotonic(),
            "last_checkpoint": "start",
            "last_completed_checkpoint": None,
            "elapsed_ms_by_checkpoint": {},
            "files_discovered": 0,
            "files_scan_attempted": 0,
            "files_scanned": 0,
            "files_read": 0,
            "files_partial_read": 0,
            "files_skipped": 0,
            "bytes_read": 0,
            "bytes_skipped_estimated": 0,
            "read_decisions": [],
            "current_root": request.workspace,
            "current_path_sample": None,
            "blocking_operation": "startup",
            "budget_exceeded_at": None,
        }

    def _record_checkpoint(self, started: float, metrics: dict[str, Any], stage: str, *, data: dict[str, object] | None = None) -> None:
        data = data or {}
        elapsed_ms = self._duration_ms(started)
        metrics["last_checkpoint"] = stage
        if stage.startswith("after_"):
            metrics["last_completed_checkpoint"] = stage
        elapsed = metrics.get("elapsed_ms_by_checkpoint")
        if not isinstance(elapsed, dict):
            elapsed = {}
        elapsed[stage] = elapsed_ms
        metrics["elapsed_ms_by_checkpoint"] = elapsed
        metrics["blocking_operation"] = self._operation_for_stage(stage)
        now = time.monotonic()
        if stage == "project_analysis_selection_started":
            metrics["_selection_started_reference"] = now
        if stage == "project_analysis_file_read_started":
            metrics["_file_read_started_reference"] = now
        for key in (
            "files_discovered",
            "files_scan_attempted",
            "files_scanned",
            "files_read",
            "files_partial_read",
            "files_skipped",
            "bytes_read",
            "bytes_skipped_estimated",
            "read_decisions",
            "current_root",
            "current_path_sample",
        ):
            if key in data and data[key] is not None:
                metrics[key] = data[key]

    def _budget_details(
        self,
        metrics: dict[str, Any],
        stage: str,
        *,
        data: dict[str, object] | None = None,
        reason_code: str | None = None,
    ) -> dict[str, object]:
        reason_code = reason_code or self._timeout_reason(stage, metrics)
        metrics["budget_exceeded_at"] = stage
        details = {
            **self._result_metric_fields(metrics),
            "checkpoint": stage,
            "elapsed_seconds": round(time.monotonic() - self._metric_started_reference(metrics), 3),
            "max_total_seconds": self.budget.max_total_seconds,
            "reason_code": reason_code,
        }
        details.update(data or {})
        return details

    def _metric_started_reference(self, metrics: dict[str, Any]) -> float:
        return float(metrics.get("_started_reference") or 0.0)

    def _stage_elapsed_exceeded(self, metrics: dict[str, Any], key: str, max_seconds: float) -> bool:
        reference = metrics.get(key)
        if reference is None or max_seconds <= 0:
            return False
        return (time.monotonic() - float(reference)) > max_seconds

    def _handoff_reserve_reached(self, started: float) -> bool:
        if not self.cooperation_policy.allow_partial_handoff:
            return False
        remaining = self._remaining_budget_ms(started)
        reserve = max(
            self.cooperation_policy.min_remaining_ms_for_handoff,
            self.cooperation_policy.min_remaining_ms_for_result_serialization,
        )
        if int(self.budget.max_total_seconds * 1000) <= reserve:
            return False
        return remaining is not None and remaining < reserve

    def _remaining_budget_ms(self, started: float) -> int | None:
        if self.budget.max_total_seconds <= 0:
            return 0
        elapsed_ms = self._duration_ms(started)
        return max(0, int(self.budget.max_total_seconds * 1000) - elapsed_ms)

    def _partial_or_blocked_handoff_result(
        self,
        request: ProjectAnalysisRequest,
        *,
        tree: ProjectTreeSummary,
        context: FileContextBundle | None,
        selection: Any,
        started: float,
        started_at: str,
        reason_code: str,
        metrics: dict[str, Any],
        data: dict[str, object] | None = None,
    ) -> ProjectAnalysisResult:
        context = context or FileContextBundle(
            bundle_id=f"file_context_{uuid4().hex}",
            workspace=tree.workspace,
            status="partial",
            warnings=[reason_code],
        )
        readiness = self._partial_readiness(tree=tree, selection=selection, context=context)
        if not readiness.safe_to_continue_to_artifact_runtime:
            return self._blocked_result(
                request,
                tree=tree,
                context=context,
                started=started,
                started_at=started_at,
                reason_code="PROJECT_ANALYSIS_INSUFFICIENT_PARTIAL_CONTEXT",
                message="Project analysis reached handoff reserve without minimum context for artifact runtime.",
                metrics=metrics,
                data={**(data or {}), "reason_code": reason_code},
            )
        metrics["budget_exceeded_at"] = str((data or {}).get("checkpoint") or metrics.get("last_checkpoint") or reason_code)
        metrics.update(
            {
                "files_discovered": max(int(metrics.get("files_discovered") or 0), len(tree.candidate_files)),
                "files_scan_attempted": max(int(metrics.get("files_scan_attempted") or 0), tree.total_files_seen),
                "files_scanned": max(int(metrics.get("files_scanned") or 0), tree.total_files_seen),
                "files_read": max(int(metrics.get("files_read") or 0), len(context.items)),
                "files_partial_read": max(int(metrics.get("files_partial_read") or 0), int((context.read_plan or {}).get("files_partial_read") or 0) if isinstance(context.read_plan, dict) else 0),
                "files_skipped": max(int(metrics.get("files_skipped") or 0), int((context.read_plan or {}).get("files_skipped") or 0) if isinstance(context.read_plan, dict) else 0),
                "bytes_read": max(int(metrics.get("bytes_read") or 0), context.total_bytes_read),
                "bytes_skipped_estimated": max(int(metrics.get("bytes_skipped_estimated") or 0), int((context.read_plan or {}).get("bytes_skipped_estimated") or 0) if isinstance(context.read_plan, dict) else 0),
                "read_decisions": list((context.read_plan or {}).get("read_decisions") or []) if isinstance(context.read_plan, dict) else list(metrics.get("read_decisions") or []),
            }
        )
        readiness.reason_codes = list(dict.fromkeys([*readiness.reason_codes, reason_code, "PROJECT_ANALYSIS_PARTIAL_HANDOFF"]))
        readiness.known_limitations = list(dict.fromkeys([*readiness.known_limitations, reason_code]))
        report = AnalysisReport(
            report_id=f"analysis_report_{uuid4().hex}",
            status="partial",
            title="Project Analysis Partial Handoff",
            summary="Project analysis returned a governed partial result before exhausting runtime budget.",
            limitations=list(readiness.known_limitations),
            warnings=list(readiness.reason_codes),
        )
        return ProjectAnalysisResult(
            result_id=f"project_analysis_{uuid4().hex}",
            workspace=context.workspace,
            status="partial",
            tree_summary=tree,
            file_context=context,
            structures=[],
            findings=[],
            report=report,
            warnings=list(dict.fromkeys([*tree.warnings, *context.warnings, *readiness.reason_codes])),
            violations=list(dict.fromkeys([*tree.violations, *context.violations])),
            trace=[
                self.trace_service.item(
                    "project_analysis",
                    "partial",
                    "PROJECT_ANALYSIS_PARTIAL_HANDOFF",
                    source="project_analysis_service",
                    data=data or {},
                )
            ],
            reason_code="PROJECT_ANALYSIS_PARTIAL_HANDOFF",
            started_at=started_at,
            finished_at=self._utc_now(),
            duration_ms=self._duration_ms(started),
            **self._result_metric_fields(metrics),
            files_scanned=int(metrics.get("files_scanned") or 0),
            files_read=len(context.items),
            bytes_read=context.total_bytes_read,
            findings_count=0,
            dependency_edges_count=0,
            partial=True,
            budget=self.budget.as_dict(),
            budget_cooperation_policy=self.cooperation_policy.as_dict(),
            file_selection_plan=getattr(selection, "plan", None),
            file_read_plan=context.read_plan,
            partial_readiness=readiness.model_dump(mode="json"),
            corpus_handoff=self._corpus_handoff_from_selection(request=request, tree=tree, selection=selection),
            files_selected=len(getattr(selection, "selected_files", []) or []),
            skipped_files_summary=self._skipped_files_summary(selection=selection, context=context),
            elapsed_ms_by_stage=self._elapsed_ms_by_stage(metrics),
            remaining_budget_ms_at_return=self._remaining_budget_ms(started),
            handoff_reserve_reached=True,
            limitations=list(readiness.known_limitations),
            safe_to_continue=True,
        )

    def _partial_readiness(
        self,
        *,
        tree: ProjectTreeSummary,
        selection: Any,
        context: FileContextBundle | None,
        corpus_handoff: dict[str, Any] | None = None,
    ) -> ProjectAnalysisPartialReadiness:
        selection_available = bool(selection is not None and getattr(selection, "selected_files", []))
        tree_available = tree.status not in {"blocked", "invalid"} and bool(tree.candidate_files or tree.total_files_seen >= 0)
        file_context_available = bool(context is not None and context.items)
        handoff_ready = bool(corpus_handoff and corpus_handoff.get("handoff_status") == "ready" and corpus_handoff.get("artifact_runtime_allowed"))
        minimum = bool(tree_available and (selection_available or handoff_ready))
        missing: list[str] = []
        if not tree_available:
            missing.append("tree_summary")
        if not selection_available and not handoff_ready:
            missing.append("file_selection")
        if not file_context_available and not handoff_ready:
            missing.append("file_context")
        safe = bool(self.cooperation_policy.allow_partial_handoff and minimum)
        confidence = 0.76 if handoff_ready else 0.72 if safe and file_context_available else 0.62 if safe else 0.0
        reason_codes = ["PROJECT_ANALYSIS_PARTIAL_CONTEXT_AVAILABLE"] if safe else ["PROJECT_ANALYSIS_INSUFFICIENT_PARTIAL_CONTEXT"]
        limitations = ["file_context_partial"] if safe and not file_context_available else []
        if handoff_ready:
            reason_codes = list(dict.fromkeys([*reason_codes, "MEDIA_CORPUS_ROOT_HANDOFF_READY"]))
            limitations = list(
                dict.fromkeys(
                    [
                        *limitations,
                        "source_reading_not_applicable_to_media_corpus",
                        "media_metadata_requires_artifact_runtime_capability",
                    ]
                )
            )
        return ProjectAnalysisPartialReadiness(
            safe_to_continue_to_artifact_runtime=safe,
            minimum_context_available=minimum,
            workspace_root_resolved=tree.status not in {"invalid"},
            tree_summary_available=tree_available,
            file_selection_available=selection_available,
            file_context_available=file_context_available,
            contract_context_available=True,
            known_limitations=limitations,
            missing_context=missing,
            reason_codes=reason_codes,
            confidence=confidence,
        )

    def _corpus_handoff_result(
        self,
        request: ProjectAnalysisRequest,
        *,
        tree: ProjectTreeSummary,
        selection: Any,
        corpus_handoff: dict[str, Any],
        started: float,
        started_at: str,
        metrics: dict[str, Any],
    ) -> ProjectAnalysisResult:
        reason_code = "MEDIA_CORPUS_ROOT_HANDOFF_READY"
        context = FileContextBundle(
            bundle_id=f"file_context_{uuid4().hex}",
            workspace=tree.workspace,
            status="partial",
            warnings=["source_reading_not_applicable_to_media_corpus"],
        )
        metrics.update(
            {
                "files_discovered": max(int(metrics.get("files_discovered") or 0), len(tree.candidate_files)),
                "files_scan_attempted": max(int(metrics.get("files_scan_attempted") or 0), tree.total_files_seen),
                "files_scanned": max(int(metrics.get("files_scanned") or 0), tree.total_files_seen),
                "files_read": 0,
                "bytes_read": 0,
            }
        )
        readiness = self._partial_readiness(tree=tree, selection=selection, context=context, corpus_handoff=corpus_handoff)
        report = AnalysisReport(
            report_id=f"analysis_report_{uuid4().hex}",
            status="partial",
            title="Project Analysis Media Corpus Handoff",
            summary="Project analysis identified a governed corpus context and handed inventory work to artifact runtime without source-readable file context.",
            limitations=list(readiness.known_limitations),
            warnings=list(readiness.reason_codes),
        )
        return ProjectAnalysisResult(
            result_id=f"project_analysis_{uuid4().hex}",
            workspace=tree.workspace,
            status="partial",
            tree_summary=tree,
            file_context=context,
            structures=[],
            findings=[],
            report=report,
            warnings=list(dict.fromkeys([*tree.warnings, *getattr(selection, "warnings", []), *readiness.reason_codes])),
            violations=list(dict.fromkeys([*tree.violations, *getattr(selection, "violations", [])])),
            trace=[
                self.trace_service.item(
                    "project_analysis",
                    "partial",
                    reason_code,
                    source="project_analysis_service",
                    data={"corpus_handoff": self._compact_corpus_handoff(corpus_handoff)},
                )
            ],
            reason_code=reason_code,
            started_at=started_at,
            finished_at=self._utc_now(),
            duration_ms=self._duration_ms(started),
            **self._result_metric_fields(metrics),
            files_scanned=int(metrics.get("files_scanned") or 0),
            files_read=0,
            bytes_read=0,
            findings_count=0,
            dependency_edges_count=0,
            partial=True,
            budget=self.budget.as_dict(),
            budget_cooperation_policy=self.cooperation_policy.as_dict(),
            file_selection_plan=getattr(selection, "plan", None),
            file_read_plan=context.read_plan,
            partial_readiness=readiness.model_dump(mode="json"),
            corpus_handoff=corpus_handoff,
            files_selected=0,
            skipped_files_summary=self._skipped_files_summary(selection=selection, context=context),
            elapsed_ms_by_stage=self._elapsed_ms_by_stage(metrics),
            remaining_budget_ms_at_return=self._remaining_budget_ms(started),
            handoff_reserve_reached=False,
            limitations=list(readiness.known_limitations),
            safe_to_continue=True,
        )

    def _corpus_handoff_from_selection(self, *, request: ProjectAnalysisRequest, tree: ProjectTreeSummary, selection: Any) -> dict[str, Any] | None:
        plan = getattr(selection, "plan", None)
        if not isinstance(plan, dict):
            return None
        root_role = str(plan.get("root_role") or self._root_role_for_workspace(request, tree.workspace) or "")
        if root_role not in {"media_corpus", "library_root", "corpus_root"}:
            return None
        inventory_count = int(plan.get("inventory_eligible_entities_count") or 0)
        source_readable_count = int(plan.get("source_readable_selected_count") or 0)
        if inventory_count <= 0:
            return {
                "handoff_status": "blocked",
                "root_role": root_role,
                "root_ref": tree.workspace,
                "source_reading_required": False,
                "source_readable_files_count": source_readable_count,
                "inventory_eligible_entities_count": 0,
                "media_entity_candidates_count": int(plan.get("media_entity_candidates_count") or 0),
                "artifact_runtime_allowed": False,
                "handoff_reason_code": "MEDIA_CORPUS_ROOT_NO_INVENTORY_ELIGIBLE_ENTITIES",
                "limitations": ["inventory_eligible_entities_missing"],
            }
        return {
            "handoff_status": "ready",
            "root_role": root_role,
            "root_ref": tree.workspace,
            "source_reading_required": False,
            "source_readable_files_count": source_readable_count,
            "inventory_eligible_entities_count": inventory_count,
            "media_entity_candidates_count": int(plan.get("media_entity_candidates_count") or 0),
            "artifact_runtime_allowed": True,
            "handoff_reason_code": "MEDIA_CORPUS_ROOT_HANDOFF_READY",
            "entity_refs_payload": {
                "kind": "file_selection_inventory_eligible_sample",
                "sample_count": len(plan.get("inventory_eligible_sample") or []),
            },
            "limitations": [
                "source_reading_not_applicable_to_media_corpus",
                "extension_used_only_as_capability_routing_hint",
                "media_metadata_requires_artifact_runtime_capability",
            ],
        }

    def _compact_corpus_handoff(self, handoff: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in handoff.items()
            if key not in {"entity_refs_payload"} or isinstance(value, (str, int, float, bool, type(None), dict))
        }

    def _root_role_for_workspace(self, request: ProjectAnalysisRequest, workspace: str) -> str | None:
        context = request.workspace_context if isinstance(request.workspace_context, dict) else {}
        workspace_norm = self._norm_path(workspace)
        for key, role in (("library_roots", "library_root"), ("corpus_roots", "corpus_root"), ("external_roots", "external_root")):
            roots = context.get(key)
            if isinstance(roots, list):
                for root in roots:
                    if self._norm_path(str(root)) == workspace_norm:
                        return role
        project_root = context.get("project_root")
        if project_root and self._norm_path(str(project_root)) == workspace_norm:
            return "source_project"
        return None

    def _norm_path(self, value: str) -> str:
        try:
            return str(Path(value).expanduser().resolve(strict=False)).casefold()
        except Exception:
            return str(value or "").casefold()

    def _skipped_files_summary(self, *, selection: Any, context: FileContextBundle | None) -> dict[str, int]:
        summary: dict[str, int] = {}
        omitted = list(getattr(selection, "omitted_files", []) or [])
        if context is not None:
            omitted.extend(context.omitted_files)
        for item in omitted:
            reason = str(getattr(item, "blocked_reason", None) or getattr(item, "reason", None) or "omitted")
            summary[reason] = summary.get(reason, 0) + 1
        return summary

    def _selection_plan_from_data(self, data: dict[str, object] | None) -> dict[str, Any] | None:
        value = (data or {}).get("file_selection_plan")
        return value if isinstance(value, dict) else None

    def _selection_plan_budget_exceeded(self, selection: Any) -> bool:
        plan = getattr(selection, "plan", None)
        return bool(isinstance(plan, dict) and plan.get("budget_exceeded"))

    def _elapsed_ms_by_stage(self, metrics: dict[str, Any]) -> dict[str, int]:
        return dict(metrics.get("elapsed_ms_by_checkpoint") or {})

    def _timeout_reason(self, stage: str, metrics: dict[str, Any]) -> str:
        if self._has_zero_progress(metrics) and stage not in {"before_path_resolution", "after_path_resolution", "before_workspace_root_scan"}:
            return "PROJECT_ANALYSIS_ZERO_PROGRESS_TIMEOUT"
        if "path_resolution" in stage:
            return "PROJECT_ANALYSIS_PATH_RESOLUTION_TIMEOUT"
        if "workspace_root_scan" in stage:
            return "PROJECT_ANALYSIS_ROOT_SCAN_TIMEOUT"
        if "file_enumeration" in stage:
            return "PROJECT_ANALYSIS_FILE_ENUMERATION_TIMEOUT"
        if "file_selection" in stage or "selection" in stage:
            return "PROJECT_ANALYSIS_FILE_SELECTION_TIMEOUT"
        if "file_read" in stage:
            return "PROJECT_ANALYSIS_FILE_READ_TIMEOUT"
        if "symbol_extraction" in stage:
            return "PROJECT_ANALYSIS_SYMBOL_EXTRACTION_TIMEOUT"
        if "result_serialization" in stage:
            return "PROJECT_ANALYSIS_RESULT_SERIALIZATION_TIMEOUT"
        return "PROJECT_ANALYSIS_INSTRUMENTATION_GAP"

    def _operation_for_stage(self, stage: str) -> str:
        if "path_resolution" in stage:
            return "path_resolution"
        if "workspace_root_scan" in stage:
            return "workspace_root_scan"
        if "file_enumeration" in stage:
            return "file_enumeration"
        if "file_selection" in stage or "selection" in stage:
            return "file_selection"
        if "file_read" in stage:
            return "file_read"
        if "symbol_extraction" in stage:
            return "symbol_extraction"
        if "result_serialization" in stage:
            return "result_serialization"
        return stage

    def _has_zero_progress(self, metrics: dict[str, Any]) -> bool:
        return not any(
            int(metrics.get(key) or 0) > 0
            for key in ("files_discovered", "files_scan_attempted", "files_scanned", "files_read", "bytes_read")
        )

    def _result_metric_fields(self, metrics: dict[str, Any]) -> dict[str, Any]:
        return {
            "last_checkpoint": metrics.get("last_checkpoint"),
            "last_completed_checkpoint": metrics.get("last_completed_checkpoint"),
            "elapsed_ms_by_checkpoint": dict(metrics.get("elapsed_ms_by_checkpoint") or {}),
            "files_discovered": int(metrics.get("files_discovered") or 0),
            "files_scan_attempted": int(metrics.get("files_scan_attempted") or 0),
            "files_partial_read": int(metrics.get("files_partial_read") or 0),
            "files_skipped": int(metrics.get("files_skipped") or 0),
            "bytes_skipped_estimated": int(metrics.get("bytes_skipped_estimated") or 0),
            "read_decisions": list(metrics.get("read_decisions") or [])[:100],
            "current_root": metrics.get("current_root"),
            "current_path_sample": metrics.get("current_path_sample"),
            "blocking_operation": metrics.get("blocking_operation"),
            "budget_exceeded_at": metrics.get("budget_exceeded_at"),
        }

    def _encoded_size(self, result: ProjectAnalysisResult) -> int:
        return len(json.dumps(result.model_dump(mode="json"), ensure_ascii=False).encode("utf-8"))

    def _duration_ms(self, started: float) -> int:
        return int((time.monotonic() - started) * 1000)

    def _utc_now(self) -> str:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()


class ProjectAnalysisBudgetExceeded(RuntimeError):
    def __init__(self, reason_code: str, message: str, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.reason_code = reason_code
        self.details = details or {}
