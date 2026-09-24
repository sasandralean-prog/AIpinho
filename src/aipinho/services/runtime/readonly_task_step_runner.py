from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from aipinho.schemas.analysis.file_selection import FileSelectionRequest
from aipinho.schemas.analysis.project_analysis_request import ProjectAnalysisRequest
from aipinho.schemas.reports.report_request import ProjectReportRequest
from aipinho.schemas.roles.role_pipeline_run import RolePipelineRunRequest
from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.schemas.runtime.task_run_context import TaskRunContext
from aipinho.schemas.runtime.task_run_step import TaskRunStep
from aipinho.schemas.tools.tool_execution import ToolExecutionRequest
from aipinho.services.analysis.project_analysis_service import ProjectAnalysisService
from aipinho.services.runtime.evidence_repair_semantic_service import (
    EvidenceRepairSemanticService,
)
from aipinho.services.reports.project_report_service import ProjectReportService
from aipinho.services.roles.role_pipeline_service import RolePipelineService
from aipinho.services.tools.read_only_execution_service import ReadOnlyExecutionService

@dataclass
class TaskStepOutcome:
    status: str
    summary: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    blocked_items: list[str] = field(default_factory=list)

class ReadOnlyTaskStepRunner:
    def __init__(self, readonly=None, analysis=None, reports=None, roles=None) -> None:
        self.readonly = readonly or ReadOnlyExecutionService()
        self.analysis = analysis or ProjectAnalysisService()
        self.reports = reports or ProjectReportService()
        self.roles = roles or RolePipelineService()

    def run(self, run: TaskRun, step: TaskRunStep, context: TaskRunContext) -> TaskStepOutcome:
        handler = getattr(self, f"_{step.step_type}", None)
        if handler is None:
            return TaskStepOutcome(status="blocked", violations=["unknown_task_step"])
        try:
            return handler(run, context)
        except Exception as exc:
            return TaskStepOutcome(status="failed", warnings=["step_dependency_failed"], violations=[str(exc)[:4000]])

    def _validate_runtime(self, run, context):
        statuses = {"readonly": self.readonly.status(), "analysis": self.analysis.status(), "reports": self.reports.status(), "roles": self.roles.status()}
        degraded = [name for name, status in statuses.items() if status.get("status") not in {"ok", "disabled"}]
        return TaskStepOutcome(status="partial" if degraded else "completed", summary={"components": {name: value.get("status") for name, value in statuses.items()}}, limitations=[f"degraded_dependency:{name}" for name in degraded])

    def _validate_workspace(self, run, context):
        if not run.workspace:
            return TaskStepOutcome(status="blocked", violations=["workspace_required"])
        result = self.readonly.execute(ToolExecutionRequest(tool_id="filesystem.inspect_path", input={"workspace": run.workspace, "path": "."}, mode="readonly", include_content=False))
        return TaskStepOutcome(status="completed" if result.status == "executed_readonly" else "blocked", summary={"execution_id": result.execution_id, "workspace": result.workspace, "target_path": result.target_path, "status": result.status}, warnings=list(result.warnings), violations=list(result.violations))

    def _request(self, run):
        continuation = (
            run.intent_map.get("mission_continuation")
            if isinstance(getattr(run, "intent_map", None), dict)
            and isinstance(run.intent_map.get("mission_continuation"), dict)
            else {}
        )
        repair = (
            dict(continuation.get("evidence_repair") or {})
            if isinstance(continuation.get("evidence_repair"), dict)
            else {}
        )
        focus_paths = [
            str(item)
            for item in list(repair.get("focus_paths") or [])
            if str(item)
        ]
        objective = str(
            getattr(getattr(run, "mission_contract", None), "objective", "")
            or run.intent_map.get("semantic_goal")
            or ""
        )
        prompt = objective
        if repair.get("required"):
            prompt = (
                f"{objective}\nEvidence repair: inspect the supplied focus paths "
                "and close only the observed evidence gaps before any side effect."
            ).strip()
        return ProjectAnalysisRequest(
            workspace=run.workspace or "",
            prompt=prompt,
            goal=(
                "evidence_repair_analysis"
                if repair.get("required")
                else "general_project_analysis"
            ),
            focus_paths=focus_paths,
            max_files=max(40, min(len(focus_paths), 100)),
            max_total_bytes=700000,
            include_trace=False,
        )

    def _build_project_tree(self, run, context):
        tree = self.analysis.tree_service.build_tree_summary(self._request(run)); context.outputs["_project_tree"] = tree
        summary = {"status": tree.status, "root_name": tree.root_name, "total_files_seen": tree.total_files_seen, "total_dirs_seen": tree.total_dirs_seen, "top_level": tree.top_level[:50], "important_paths": tree.important_paths[:50], "candidate_files_count": len(tree.candidate_files), "blocked_paths_count": len(tree.blocked_paths)}
        status = "completed" if tree.status == "ok" else ("partial" if tree.status in {"partial", "degraded"} else "blocked")
        return TaskStepOutcome(status=status, summary=summary, warnings=list(tree.warnings), violations=list(tree.violations), limitations=list(tree.warnings), blocked_items=list(tree.blocked_paths[:100]))

    def _build_file_context(self, run, context):
        request = self._request(run); tree = context.outputs.get("_project_tree") or self.analysis.tree_service.build_tree_summary(request)
        selection = self.analysis.selection_service.select_files(
            FileSelectionRequest(
                workspace=request.workspace,
                goal=request.goal,
                semantic_query=request.prompt,
                candidate_files=list(tree.candidate_files),
                focus_paths=request.focus_paths,
                max_files=request.max_files,
                max_total_bytes=request.max_total_bytes,
            ),
            project_tree=tree,
        )
        bundle = self.analysis.context_builder.build_context(request, selection); context.outputs["_file_context"] = bundle
        semantic_outcome = self._file_context_semantic_outcome(bundle)
        summary = {"status": bundle.status, "bundle_id": bundle.bundle_id, "included_files": len([item for item in bundle.items if item.status == "included"]), "omitted_files": [getattr(item, "path", str(item)) for item in bundle.omitted_files[:100]], "total_bytes_read": bundle.total_bytes_read, "semantic_outcome": semantic_outcome}
        status = "completed" if bundle.status == "ok" else ("partial" if bundle.status == "partial" else "blocked")
        return TaskStepOutcome(status=status, summary=summary, warnings=list(bundle.warnings), violations=list(bundle.violations), limitations=["file_context_budget_or_omissions"] if bundle.status == "partial" else [], blocked_items=[getattr(item, "path", str(item)) for item in bundle.omitted_files[:100]])

    def _file_context_semantic_outcome(self, bundle) -> dict[str, Any]:
        status = str(getattr(bundle, "status", "") or "")
        if status == "ok":
            safety: bool | str = True
        elif status == "partial":
            safety = "true_with_limitations"
        else:
            safety = False

        limitations = list(getattr(bundle, "warnings", []) or [])
        if status == "partial" and "file_context_budget_or_omissions" not in limitations:
            limitations.append("file_context_budget_or_omissions")
        missing_truth = list(getattr(bundle, "violations", []) or [])
        omitted_files = list(getattr(bundle, "omitted_files", []) or [])
        if omitted_files and "file_context_omitted_files_present" not in limitations:
            limitations.append("file_context_omitted_files_present")

        return {
            "use_safety": {
                "safe_for_downstream_static_analysis": safety,
            },
            "limitations": list(dict.fromkeys(str(item) for item in limitations if str(item))),
            "missing_truth": list(dict.fromkeys(str(item) for item in missing_truth if str(item))),
            "required_disclosures": list(dict.fromkeys(str(item) for item in limitations if str(item))),
        }

    def _run_project_analysis(self, run, context):
        result = self.analysis.analyze_project(self._request(run)); context.outputs["_project_analysis"] = result
        semantic_outcome = self._project_analysis_semantic_outcome(
            result,
            repair=self._evidence_repair_context(run),
        )
        summary = {"status": result.status, "result_id": result.result_id, "structures": list(result.structures), "findings_count": len(result.findings), "finding_summaries": [{"title": item.title, "severity": item.severity, "summary": item.summary} for item in result.findings[:20]], "semantic_outcome": semantic_outcome}
        status = "completed" if result.status == "ok" else ("partial" if result.status in {"partial", "degraded"} else "blocked")
        return TaskStepOutcome(status=status, summary=summary, warnings=list(result.warnings), violations=list(result.violations), limitations=list(dict.fromkeys([*list(result.warnings), *list(result.limitations)])))

    def _project_analysis_semantic_outcome(
        self,
        result,
        *,
        repair: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        nonfatal = list(
            self.analysis.selection_service.settings.get(
                "nonfatal_omission_violations",
                [],
            )
            or []
        )
        return EvidenceRepairSemanticService.project_analysis_outcome(
            result,
            repair=repair,
            nonfatal_omission_reasons=nonfatal,
        )

    def _evidence_repair_context(self, run) -> dict[str, Any]:
        return EvidenceRepairSemanticService.context(run)

    def _generate_project_report(self, run, context):
        execution_metadata = self._execution_plan_metadata(run)
        response = self.reports.generate_report(
            ProjectReportRequest(
                workspace=run.workspace,
                goal="general",
                include_trace=False,
                requested_deliverables=list(execution_metadata.get("requested_deliverables", [])),
                workspace_references=list(execution_metadata.get("workspace_references", [])),
            )
        ); report = response.report; context.outputs["_project_report"] = response
        summary = {"status": response.status, "report_id": report.report_id if report else None, "executive_summary": report.executive_summary if report else "", "findings_count": len(report.findings) if report else 0, "limitations": list(report.limitations) if report else list(response.warnings), "requested_deliverables": list(report.requested_deliverables) if report else [], "fulfilled_deliverables": list(report.fulfilled_deliverables) if report else [], "missing_deliverables": list(report.missing_deliverables) if report else [], "rendered_markdown": (response.rendered_markdown or "")[:30000]}
        status = "completed" if response.status in {"ok", "completed"} else ("partial" if response.status in {"partial", "degraded"} else "failed")
        return TaskStepOutcome(status=status, summary=summary, warnings=list(response.warnings), limitations=list(report.limitations) if report else list(response.warnings))

    def _run_role_pipeline(self, run, context):
        report = context.outputs.get("_project_report") or context.outputs.get("project_report") or {}; bundle = context.outputs.get("_file_context") or context.outputs.get("file_context_bundle") or {}
        report_dict = report.model_dump() if hasattr(report, "model_dump") else report; bundle_dict = bundle.model_dump() if hasattr(bundle, "model_dump") else bundle
        execution_plan = run.plan.canonical_execution_plan if run.plan else None
        role_intent = {
            "intent_type": execution_plan.operation_kind if execution_plan else run.contract_type,
            "semantic_goal": execution_plan.semantic_goal if execution_plan else run.contract_type,
            "required_capabilities": list(execution_plan.required_capabilities if execution_plan else run.capabilities_required),
        }
        role_run = self.roles.run_pipeline(RolePipelineRunRequest(
            pipeline_id=None,
            intent_map=role_intent,
            policy_decision=run.policy_snapshot,
            task_draft={"contract_type": run.contract_type, "requested_actions": run.requested_actions},
            project_report=report_dict if isinstance(report_dict, dict) else {},
            file_context_bundle=bundle_dict if isinstance(bundle_dict, dict) else {},
            context_injection_plan_id=run.context_injection_plan_id,
            context_injection_plan=context.outputs.get("context_injection_plan") or {},
            evidence=(
                list(context.outputs.get("evidence_context") or [])
                if isinstance(context.outputs.get("evidence_context"), list)
                else []
            ),
            session_id=run.session_id,
            mode="run",
            model_mode="deterministic",
            allow_real_inference=False,
            operator_confirmed=False,
            parent_task_run_id=run.run_id,
            parent_operation_id=run.operation_id,
            parent_execution_id=execution_plan.execution_id if execution_plan else None,
        ))
        context.outputs["_role_pipeline"] = role_run
        summary = {"run_id": role_run.run_id, "pipeline_id": role_run.pipeline_id, "status": role_run.status, "passes": [{"role_id": item.role_id, "status": item.status} for item in role_run.passes], "final_output": role_run.final_output}
        status = "completed" if role_run.status == "completed" else ("partial" if role_run.status in {"partial", "degraded"} else "failed")
        return TaskStepOutcome(status=status, summary=summary, warnings=list(role_run.warnings), limitations=list(role_run.warnings))

    def _compose_final_result(self, run, context):
        return TaskStepOutcome(status="completed", summary={"outputs_available": sorted(key.lstrip("_") for key in context.outputs), "limitations": len(context.limitations), "blocked_items": len(context.blocked_items)})

    def _execution_plan_metadata(self, run) -> dict[str, Any]:
        execution_plan = run.plan.canonical_execution_plan if run.plan else None
        if execution_plan is None:
            return {}
        return execution_plan.metadata if isinstance(execution_plan.metadata, dict) else {}

    def status(self):
        return {"status": "ok", "service": "readonly_task_step_runner", "write_enabled": False, "patch_enabled": False, "shell_enabled": False, "real_model_auto_use": False}

