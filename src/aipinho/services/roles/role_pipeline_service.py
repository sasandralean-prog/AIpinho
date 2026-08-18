from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.roles.role_pass_input import RolePassInput
from aipinho.schemas.roles.role_pipeline_run import RolePipelineRun, RolePipelineRunRequest
from aipinho.schemas.rag.integration.contracts import ContextInjectionPlan
from aipinho.services.rag.integration.context_injection_planner import ContextInjectionPlanner
from aipinho.services.rag.integration.context_usage_validator import ContextUsageValidator
from aipinho.services.roles.role_pass_runner import RolePassRunner
from aipinho.services.roles.role_pipeline_audit_service import RolePipelineAuditService
from aipinho.services.roles.role_pipeline_config_service import RolePipelineConfigService
from aipinho.services.roles.role_pipeline_planner import RolePipelinePlanner
from aipinho.services.roles.role_pipeline_trace_service import RolePipelineTraceService
from aipinho.services.roles.role_model_binding_service import RoleModelBindingService
from aipinho.services.semantic_runtime.capability_resolver import CapabilityResolver
from aipinho.utils.safe_paths import resolve_within_root
from aipinho.utils.yaml_loader import load_yaml_file


class RolePipelineService:
    def __init__(self, config_service: RolePipelineConfigService | None = None, runner: RolePassRunner | None = None, audit: RolePipelineAuditService | None = None, trace: RolePipelineTraceService | None = None) -> None:
        self.config_service = config_service or RolePipelineConfigService()
        self.planner = RolePipelinePlanner(self.config_service)
        self.runner = runner or RolePassRunner()
        self.audit = audit or RolePipelineAuditService()
        self.trace_service = trace or RolePipelineTraceService()
        self.policy = load_yaml_file(PATHS.config_root / "roles" / "role_pipeline_policy.yaml", critical=True, root=PATHS.config_root / "roles")
        self.runs_dir = PATHS.project_root / "data" / "runtime" / "role_pipeline_runs"
        self.context_planner = ContextInjectionPlanner()
        self.context_validator = ContextUsageValidator()
        self.model_bindings = RoleModelBindingService()
        self.capability_resolver = CapabilityResolver(role_binding_service=self.model_bindings)

    def list_pipelines(self) -> dict[str, object]:
        return {pid: pipeline.model_dump() for pid, pipeline in self.config_service.list_pipelines().items()}

    def get_pipeline(self, pipeline_id: str) -> dict[str, object] | None:
        pipeline = self.config_service.get_pipeline(pipeline_id)
        return pipeline.model_dump() if pipeline else None

    def preview_pipeline(self, request: RolePipelineRunRequest) -> RolePipelineRun:
        pipeline_id = self.planner.choose_pipeline(request)
        pipeline = self.config_service.get_pipeline(pipeline_id)
        run = RolePipelineRun(pipeline_id=pipeline_id, status="preview", input_summary=self._summary(request))
        if pipeline is None or not pipeline.enabled:
            run.warnings.append("pipeline_disabled_or_unknown")
            run.finish("failed")
            return self._save(run)
        missing = self._missing_inputs(pipeline, request)
        context_warnings = self._context_plan_warnings(request)
        if context_warnings:
            missing.extend(context_warnings)
        if missing:
            run.warnings.extend(missing)
            run.trace.append(self.trace_service.item("input_validation", "needs_input", ",".join(missing)))
            run.finish("needs_input")
            return self._save(run)
        for definition in pipeline.passes:
            role_input = self._role_input(definition, request, mode="preview")
            role_pass = self.runner.preview(role_input)
            run.passes.append(role_pass)
            run.trace.append(self.trace_service.item("pass_preview", role_pass.status, role_id=definition.role_id, pass_id=definition.pass_id))
        run.final_output = {"source": "preview", "side_effects": False, "model_invoked": False}
        run.finish("preview")
        return self._save(run)

    def run_pipeline(self, request: RolePipelineRunRequest) -> RolePipelineRun:
        pipeline_id = self.planner.choose_pipeline(request)
        pipeline = self.config_service.get_pipeline(pipeline_id)
        run = RolePipelineRun(pipeline_id=pipeline_id, status="degraded", input_summary=self._summary(request))
        if pipeline is None or not pipeline.enabled:
            run.warnings.append("pipeline_disabled_or_unknown")
            run.finish("failed")
            return self._save(run)
        missing = self._missing_inputs(pipeline, request)
        context_warnings = self._context_plan_warnings(request)
        if context_warnings:
            missing.extend(context_warnings)
        if missing:
            run.warnings.extend(missing)
            run.finish("needs_input")
            return self._save(run)
        stop_on_required = bool(self.policy.get("role_pipeline", {}).get("stop_on_required_pass_failure", True))
        continue_optional = bool(self.policy.get("role_pipeline", {}).get("continue_on_optional_pass_failure", True))
        stopped = False
        for definition in pipeline.passes:
            role_input = self._role_input(definition, request, mode="run")
            role_pass = self.runner.run(role_input)
            run.passes.append(role_pass)
            eval_status = role_pass.evaluation_result.get("status") if isinstance(role_pass.evaluation_result, dict) else None
            self.audit.record(run_id=run.run_id, pipeline_id=run.pipeline_id, pass_id=definition.pass_id, role_id=definition.role_id, status=role_pass.status, model_id=role_pass.model_gate.model_id if role_pass.model_gate else None, real_inference=bool(role_pass.model_gate.real_inference) if role_pass.model_gate else False, evaluation_status=str(eval_status) if eval_status else None)
            run.trace.append(self.trace_service.item("pass_run", role_pass.status, role_id=definition.role_id, pass_id=definition.pass_id))
            if role_pass.required and role_pass.status in {"failed", "rejected"} and stop_on_required:
                stopped = True
                run.warnings.append(f"required_pass_failed:{definition.pass_id}")
                break
            if (not role_pass.required) and role_pass.status in {"failed", "rejected"} and continue_optional:
                run.warnings.append(f"optional_pass_failed:{definition.pass_id}")
        completed = [p for p in run.passes if p.status == "completed"]
        rejected_required = [p for p in run.passes if p.required and p.status in {"failed", "rejected"}]
        last_output = completed[-1].output if completed and completed[-1].output else None
        real_inference = any(bool(item.model_gate and item.model_gate.real_inference) for item in run.passes)
        run.final_output = {
            "source": last_output.source if last_output else "fallback",
            "content_preview": (last_output.content[:500] if last_output else ""),
            "side_effects": False,
            "real_inference": real_inference,
            "tools": False,
            "write": False,
            "patch": False,
            "stopped": stopped,
        }
        if rejected_required:
            run.finish("rejected")
        elif len(completed) == len(run.passes):
            run.finish("completed")
        elif completed:
            run.finish("partial")
        else:
            run.finish("failed")
        return self._save(run)

    def get_run(self, run_id: str) -> RolePipelineRun | None:
        path = self._run_path(run_id)
        if not path.exists():
            return None
        return RolePipelineRun.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def get_trace(self, run_id: str) -> list[dict[str, object]]:
        run = self.get_run(run_id)
        return [item.model_dump() for item in run.trace] if run else []

    def status(self) -> dict[str, object]:
        safety = self.policy.get("safety", {}) if isinstance(self.policy.get("safety", {}), dict) else {}
        role_pipeline = self.policy.get("role_pipeline", {}) if isinstance(self.policy.get("role_pipeline", {}), dict) else {}
        return {
            "status": "ok",
            "service": "role_pipeline",
            "enabled": bool(role_pipeline.get("enabled", True)),
            "pipelines": len(self.config_service.list_pipelines()),
            "real_inference_auto_use": bool(role_pipeline.get("real_inference_auto_use", False)),
            "manual_real_inference_in_pipeline_enabled": bool(role_pipeline.get("allow_manual_real_inference", True)),
            "tools_enabled": bool(safety.get("tools_enabled", False)),
            "write_enabled": bool(safety.get("write_enabled", False)),
            "patch_enabled": bool(safety.get("patch_enabled", False)),
            "shell_enabled": bool(safety.get("shell_enabled", False)),
            "rag_enabled": bool(safety.get("rag_enabled", False)),
            "memory_write_enabled": bool(safety.get("memory_write_enabled", False)),
            "model_tool_calling_enabled": bool(safety.get("model_tool_calling_enabled", False)),
            "context_injection_plan_enabled": True,
            "role_source_selection_enabled": False,
            "curated_memory_context_enabled": False,
            "role_model_bindings": self.model_bindings.status(),
            "silent_stub_fallback": False,
        }

    def _role_input(self, definition: Any, request: RolePipelineRunRequest, *, mode: str) -> RolePassInput:
        binding = self.model_bindings.resolve_binding(definition.role_id)
        role_policy = self.policy.get("role_pipeline", {}) if isinstance(self.policy.get("role_pipeline", {}), dict) else {}
        runtime_policy = self.policy.get("task_runtime", {}) if isinstance(self.policy.get("task_runtime", {}), dict) else {}
        real_auto = bool(role_policy.get("real_inference_auto_use", False) or runtime_policy.get("allow_real_inference", False))
        binding_default_real = bool(binding and getattr(binding, "default_real_inference", False))
        real_requested = bool(
            request.allow_real_inference
            or request.model_mode == "manual_real"
            or (request.model_mode not in {"deterministic", "stub"} and real_auto and binding_default_real)
        )
        if request.model_mode == "deterministic" and binding and binding.fallback_model and binding.fallback_model.startswith("deterministic_"):
            model_id = binding.fallback_model
            model_mode = "deterministic"
        else:
            capability_selection = self.capability_resolver.resolve_for_role(definition.role_id) if real_requested and binding and binding.enabled else None
            model_id = capability_selection.selected_model_id if capability_selection and capability_selection.allowed else "stub.default"
            model_mode = "manual_real" if real_requested else "stub"
        return RolePassInput(pass_id=definition.pass_id, role_id=definition.role_id, required=definition.required, user_message=request.user_message, purpose=self._purpose_for_role(definition.role_id, request), intent_map=request.intent_map, policy_decision=request.policy_decision, task_contract=request.task_draft, project_report=request.project_report, file_context_bundle=request.file_context_bundle, context_injection_plan_id=request.context_injection_plan_id, context_injection_plan=request.context_injection_plan, evidence=request.evidence or self._evidence_from_report(request.project_report), session_id=request.session_id, mode=mode, model_mode=model_mode, requested_model_id=model_id, allow_real_inference=real_requested, operator_confirmed=bool(request.operator_confirmed or (real_requested and real_auto)), include_trace=request.include_trace)

    def _purpose_for_role(self, role_id: str, request: RolePipelineRunRequest) -> str:
        if role_id == "analyst":
            return "code_analysis"
        if role_id == "reporter":
            return "project_report"
        if role_id == "planner":
            return "task_preview"
        if role_id in {"supervisor", "validator"}:
            return "validation"
        if role_id == "debugger":
            return "debug_trace"
        return "chat"

    def _missing_inputs(self, pipeline: Any, request: RolePipelineRunRequest) -> list[str]:
        missing: list[str] = []
        required = set(pipeline.required_inputs or [])
        if "file_context_bundle_or_project_report" in required and not request.file_context_bundle and not request.project_report:
            missing.append("file_context_bundle_or_project_report_required")
        return missing

    def _summary(self, request: RolePipelineRunRequest) -> dict[str, object]:
        return {"intent_type": request.intent_map.get("intent_type") if isinstance(request.intent_map, dict) else None, "mode": request.mode, "model_mode": request.model_mode, "has_project_report": bool(request.project_report), "has_file_context_bundle": bool(request.file_context_bundle), "context_injection_plan_id": request.context_injection_plan_id or request.context_injection_plan.get("plan_id"), "evidence_items": len(request.evidence)}

    def _context_plan_warnings(self, request: RolePipelineRunRequest) -> list[str]:
        if not request.context_injection_plan and not request.context_injection_plan_id:
            return []
        try:
            plan = (
                ContextInjectionPlan.model_validate(request.context_injection_plan)
                if request.context_injection_plan
                else self.context_planner.get_plan(str(request.context_injection_plan_id))
            )
        except (ValueError, TypeError):
            return ["context_injection_plan_invalid"]
        if plan is None:
            return ["context_injection_plan_not_found"]
        validation = self.context_validator.validate_plan(plan)
        warnings = list(validation.violations)
        if any(item.kind == "curated_memory" for item in plan.context_items):
            warnings.append("role_pipeline_curated_memory_blocked_by_default")
        return list(dict.fromkeys(warnings))

    def _evidence_from_report(self, report: dict[str, object]) -> list[dict[str, object]]:
        if not isinstance(report, dict):
            return []
        nested_report = report.get("report") if isinstance(report.get("report"), dict) else {}
        evidence = (
            report.get("evidence")
            or report.get("evidence_index")
            or nested_report.get("evidence")
            or nested_report.get("evidence_index")
            or []
        )
        return [item for item in evidence if isinstance(item, dict)] if isinstance(evidence, list) else []

    def _run_path(self, run_id: str) -> Path:
        return resolve_within_root(self.runs_dir / f"{run_id}.json", PATHS.project_root)

    def _save(self, run: RolePipelineRun) -> RolePipelineRun:
        if run.status != "preview" and run.validation_summary is None:
            try:
                from aipinho.services.validation.validation_gate_service import ValidationGateService
                validation = ValidationGateService().validate_role_pipeline_object(run)
                run.validation_summary = validation.summary()
                if run.status == "completed" and validation.status in {"failed", "rejected"}:
                    run.finish("rejected")
                elif run.status == "completed" and validation.status in {"degraded", "needs_review"}:
                    run.finish("degraded")
                if validation.status in {"failed", "rejected", "degraded", "needs_review"}:
                    run.warnings = list(dict.fromkeys([*run.warnings, f"validation_status:{validation.status}"]))
            except Exception as exc:
                run.validation_summary = {"status": "degraded", "score": 0.0, "safe_to_display": True, "warnings": ["validation_dependency_failed", str(exc)[:500]], "blocking_findings": []}
                run.warnings = list(dict.fromkeys([*run.warnings, "validation_dependency_failed"]))
        path = self._run_path(run.run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(run.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
        return run

