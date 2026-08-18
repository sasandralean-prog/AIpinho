from __future__ import annotations
from typing import Any
from aipinho.core.paths import PATHS
from aipinho.schemas.runtime.task_run_result import TaskRunResult
from aipinho.services.runtime.task_run_store import TaskRunStore
from aipinho.utils.yaml_loader import load_yaml_file

class TaskRunResultService:
    def __init__(self, store=None):
        self.store = store or TaskRunStore()
        self.policy = load_yaml_file(PATHS.config_root / "runtime" / "task_result_policy.yaml", critical=True, root=PATHS.config_root / "runtime")

    def build(self, run, context, *, events_count: int) -> TaskRunResult:
        outputs: dict[str, Any] = {}
        step_summaries = [{"step_id": s.step_id, "step_type": s.step_type, "status": s.status, "output_summary": s.output_summary, "warnings": s.warnings, "violations": s.violations} for s in run.plan.steps]
        mapping = {
            "build_project_tree": "project_tree_summary",
            "build_file_context": "file_context_summary",
            "run_project_analysis": "project_analysis_report",
            "generate_project_report": "project_report",
            "run_role_pipeline": "role_pipeline_run",
            "execute_patch_pipeline": "patch_result",
            "validate_patch_result": "validation_result",
            "execute_project_generation": "project_generation",
            "validate_project_result": "validation_result",
            "execute_governed_shell": "command_result",
            "validate_shell_result": "validation_result",
        }
        for step_type, target in mapping.items():
            item = next((entry for entry in step_summaries if entry["step_type"] == step_type), None)
            if item and item["status"] in {"completed", "partial"}: outputs[target] = item["output_summary"]
        limitations = list(dict.fromkeys([*context.limitations, *[warning for step in run.plan.steps if step.status == "partial" for warning in step.warnings]]))
        blocked_values = [*context.blocked_items, *[violation for step in run.plan.steps if step.status == "blocked" for violation in step.violations]]
        blocked = list(dict.fromkeys(str(getattr(item, "path", item)) for item in blocked_values))
        if run.status == "partial" and not limitations: limitations.append("one_or_more_steps_completed_partially")
        result_status = run.status if run.status in {"completed","partial","failed","cancelled","blocked"} else "failed"
        completion = context.outputs.get("_completion")
        execution_label = self._execution_label(run)
        result = TaskRunResult(run_id=run.run_id, status=result_status, reason_code=self._reason_code(run, result_status, blocked), summary=self._summary(run, outputs, limitations), outputs=self.store.sanitize(outputs), step_summaries=self.store.sanitize(step_summaries), limitations=limitations, blocked_items=blocked, warnings=list(dict.fromkeys([*run.warnings,*context.warnings])), events_count=events_count, trace_ref=f"task-runs/{run.run_id}/trace", safe_to_display=True, block_cause=run.block_cause, completion=completion)
        try:
            from aipinho.services.validation.validation_gate_service import ValidationGateService
            validation = ValidationGateService().validate_task_run_object(run, result=result, events=self.store.get_events(run.run_id))
            result.validation = validation.summary()
            if result.status in {"failed", "blocked", "cancelled"} and result.validation.get("status") == "passed":
                result.validation["status"] = "blocked" if result.status == "blocked" else "failed"
                result.validation["score"] = 0.0
                result.validation["blocking_findings"] = list(
                    dict.fromkeys(
                        [
                            *[str(item) for item in result.validation.get("blocking_findings", []) or []],
                            f"task_run_status:{result.status}",
                        ]
                    )
                )
            if result.block_cause is not None:
                result.block_cause.validation_status = str(result.validation.get("status") or validation.status)
                result.block_cause.validation_id = getattr(validation, "validation_id", None)
            effective_validation_status = str(result.validation.get("status") or validation.status)
            if effective_validation_status in {"failed", "rejected", "degraded", "needs_review", "blocked"}:
                limitation = f"validation_status:{effective_validation_status}"
                result.warnings = list(dict.fromkeys([*result.warnings, limitation]))
                result.limitations = list(dict.fromkeys([*result.limitations, limitation]))
                if result.status == "completed":
                    result.status = "partial"
                    result.summary = self._summary_for_status("partial", outputs, result.limitations, execution_label=execution_label)
                result.safe_to_display = validation.safe_to_display
        except Exception as exc:
            result.validation = {"status": "degraded", "score": 0.0, "safe_to_display": True, "warnings": ["validation_dependency_failed", str(exc)[:500]], "blocking_findings": []}
            result.warnings = list(dict.fromkeys([*result.warnings, "validation_dependency_failed"]))
        return result

    def _summary(self, run, outputs, limitations):
        return self._summary_for_status(run.status, outputs, limitations, block_cause=run.block_cause, execution_label=self._execution_label(run))

    def _summary_for_status(self, status, outputs, limitations, *, block_cause=None, execution_label="governada"):
        if status == "completed": return f"TaskRun {execution_label} concluida com {len(outputs)} grupo(s) de resultado."
        if status == "partial": return f"TaskRun {execution_label} concluida parcialmente com {len(limitations)} limitacao(oes) explicita(s)."
        if status == "cancelled": return "TaskRun cancelada; nenhum novo step sera executado."
        if status == "blocked" and block_cause:
            return f"TaskRun bloqueada em {block_cause.blocked_stage}: {block_cause.human_reason}"
        if status == "blocked": return "TaskRun bloqueada; consulte a causa estruturada e o trace."
        return "TaskRun falhou de forma controlada; consulte steps, eventos e trace sanitizado."

    def _execution_label(self, run) -> str:
        contract_type = str(getattr(run, "contract_type", "") or "")
        mode = str(getattr(run, "mode", "") or "")
        if mode == "read_only" or contract_type.startswith("readonly"):
            return "read-only"
        return "governada"

    def _reason_code(self, run, result_status: str, blocked_items: list[str]) -> str | None:
        if result_status == "completed":
            return None
        cause = getattr(run, "block_cause", None)
        if cause and getattr(cause, "block_reason_code", None):
            return str(cause.block_reason_code)
        blocked_reasons = getattr(run, "blocked_reasons", None)
        if blocked_reasons:
            return str(blocked_reasons[0])
        if blocked_items:
            return str(blocked_items[0])
        if result_status in {"blocked", "failed", "cancelled"}:
            return f"task_run_{result_status}"
        return None

    def status(self): return {"status":"ok","service":"task_run_result","safe_to_display":True,"raw_content_enabled":False}


