from __future__ import annotations
from typing import Any
from aipinho.schemas.rag.integration.contracts import ContextInjectionPlan
from aipinho.services.rag.integration.context_usage_validator import ContextUsageValidator
from aipinho.services.validation.validation_common import as_dict, finding
from aipinho.services.validation.contract_compliance_validator import ContractComplianceValidator
from aipinho.services.validation.evidence_compliance_validator import EvidenceComplianceValidator
from aipinho.services.validation.gate_decision_service import GateDecisionService
from aipinho.services.validation.policy_compliance_validator import PolicyComplianceValidator
from aipinho.services.validation.report_quality_gate_service import ReportQualityGateService
from aipinho.services.validation.role_pipeline_validator import RolePipelineValidator
from aipinho.services.validation.side_effect_validator import SideEffectValidator
from aipinho.services.validation.task_result_validator import TaskResultValidator
from aipinho.services.validation.task_run_validator import TaskRunValidator
from aipinho.services.validation.validation_store import ValidationStore
from aipinho.services.validation.validation_trace_service import ValidationTraceService
from aipinho.services.validation.workspace_access_validator import WorkspaceAccessValidator
from aipinho.utils.yaml_loader import inspect_yaml_file
from aipinho.core.paths import PATHS

class ValidationGateService:
    CONFIGS = [
        "validation_gate_policy.yaml", "task_run_validation_policy.yaml", "report_quality_gate_policy.yaml",
        "contract_compliance_policy.yaml", "evidence_compliance_policy.yaml", "side_effect_validation_policy.yaml",
        "workspace_access_validation_policy.yaml", "quality_score_policy.yaml", "validation_audit_policy.yaml", "validation_store_policy.yaml",
    ]

    def __init__(self, store: ValidationStore | None = None) -> None:
        self.store = store or ValidationStore()
        self.trace = ValidationTraceService()
        self.decision = GateDecisionService()
        self.task_run_validator = TaskRunValidator()
        self.task_result_validator = TaskResultValidator()
        self.report_quality = ReportQualityGateService(store=self.store)
        self.role_pipeline_validator = RolePipelineValidator()
        self.side_effect_validator = SideEffectValidator()
        self.evidence_validator = EvidenceComplianceValidator()
        self.contract_validator = ContractComplianceValidator()
        self.policy_validator = PolicyComplianceValidator()
        self.workspace_validator = WorkspaceAccessValidator()
        self.context_usage_validator = ContextUsageValidator()

    def validate_request(self, request) :
        target_type = request.target_type
        if target_type == "task_run" and request.target_id:
            return self.validate_task_run_id(request.target_id)
        if target_type == "task_result":
            return self.validate_task_result_payload(request.payload)
        if target_type == "project_report":
            return self.validate_report_payload(request.payload, target_id=request.target_id)
        if target_type == "role_pipeline_run" and request.target_id:
            return self.validate_role_pipeline_id(request.target_id)
        if target_type == "side_effects":
            return self.validate_side_effects(request.payload)
        if target_type == "evidence":
            return self.validate_evidence(request.payload)
        if target_type == "context_usage":
            return self.validate_context_usage(request.payload)
        return self._result(target_type=target_type, target_id=request.target_id, findings=[], warnings=["unsupported_or_missing_target"], metadata={"request": request.model_dump() if hasattr(request, "model_dump") else {}})

    def validate_task_run_id(self, run_id: str):
        from aipinho.services.runtime.task_run_store import TaskRunStore
        store = TaskRunStore()
        run = store.get_run(run_id)
        result = store.get_result(run_id)
        events = store.get_events(run_id)
        if run is None:
            return self._result(target_type="task_run", target_id=run_id, findings=[], warnings=["task_run_not_found"], validator_error=True)
        return self.validate_task_run_object(run, result=result, events=events)

    def validate_task_run_object(self, run: Any, *, result: Any | None = None, events: Any | None = None):
        data = as_dict(run)
        findings = self.task_run_validator.validate(data, result=result, events=events or [])
        return self._result(target_type="task_run", target_id=data.get("run_id"), findings=findings, metadata={"events": len(events or [])})

    def validate_task_result_payload(self, payload: Any):
        findings = self.task_result_validator.validate(payload)
        return self._result(target_type="task_result", target_id=as_dict(payload).get("run_id"), findings=findings)

    def validate_report_payload(self, payload: Any, *, target_id: str | None = None):
        return self.report_quality.validate_report(payload, target_id=target_id)

    def validate_report_id(self, report_id: str):
        from aipinho.services.reports.project_report_service import ProjectReportService
        report = ProjectReportService().get_report(report_id)
        if report is None:
            return self._result(target_type="project_report", target_id=report_id, findings=[], warnings=["report_not_found"], validator_error=True)
        return self.validate_report_payload(report, target_id=report_id)

    def validate_role_pipeline_id(self, run_id: str):
        from aipinho.services.roles.role_pipeline_service import RolePipelineService
        run = RolePipelineService().get_run(run_id)
        if run is None:
            return self._result(target_type="role_pipeline_run", target_id=run_id, findings=[], warnings=["role_pipeline_run_not_found"], validator_error=True)
        return self.validate_role_pipeline_object(run)

    def validate_role_pipeline_object(self, run: Any):
        data = as_dict(run)
        findings = self.role_pipeline_validator.validate(data)
        return self._result(target_type="role_pipeline_run", target_id=data.get("run_id"), findings=findings)

    def validate_side_effects(self, payload: Any):
        findings = self.side_effect_validator.validate(payload)
        return self._result(target_type="side_effects", target_id=None, findings=findings)

    def validate_evidence(self, payload: Any):
        findings = self.evidence_validator.validate(payload)
        return self._result(target_type="evidence", target_id=None, findings=findings)

    def validate_context_usage(self, payload: Any):
        data = as_dict(payload)
        raw_plan = data.get("plan") or data.get("context_injection_plan")
        if not isinstance(raw_plan, dict):
            return self._result(
                target_type="context_usage",
                target_id=data.get("plan_id"),
                findings=[finding("context_injection_plan_required", "Context plan required", "Context usage validation requires a ContextInjectionPlan.", severity="error", validator="context_usage")],
            )
        try:
            plan = ContextInjectionPlan.model_validate(raw_plan)
        except Exception:
            return self._result(
                target_type="context_usage",
                target_id=data.get("plan_id"),
                findings=[finding("context_injection_plan_invalid", "Context plan invalid", "The supplied ContextInjectionPlan does not match the governed schema.", severity="error", validator="context_usage")],
            )
        validation = self.context_usage_validator.validate_output(str(data.get("output") or ""), plan)
        findings = [
            finding(code.split(":", 1)[0], "Context usage violation", code, severity="error", validator="context_usage", evidence=[code])
            for code in validation.violations
        ]
        findings.extend(
            finding(code, "Context usage warning", code, severity="warning", validator="context_usage", evidence=[code])
            for code in validation.warnings
        )
        return self._result(
            target_type="context_usage",
            target_id=plan.plan_id,
            findings=findings,
            metadata={"context_usage": validation.model_dump()},
        )

    def get_result(self, validation_id: str): return self.store.get_result(validation_id)
    def get_trace(self, validation_id: str): return self.store.get_trace(validation_id)

    def _result(self, *, target_type: str, target_id: str | None, findings: list, warnings: list[str] | None = None, metadata: dict | None = None, validator_error: bool = False):
        trace = [self.trace.item("validation_gate", "checked", "deterministic_validators_applied", source="config/validation/validation_gate_policy.yaml", data={"findings": len(findings), "validator_error": validator_error})]
        result = self.decision.build_result(target_type=target_type, target_id=target_id, findings=findings, warnings=warnings or [], trace=trace, metadata=metadata or {}, validator_error=validator_error)
        return self.store.save_result(result)

    def status(self) -> dict[str, object]:
        configs = {name: inspect_yaml_file(PATHS.config_root / "validation" / name, root=PATHS.project_root).__dict__ for name in self.CONFIGS}
        warnings = [f"{name}:{value.get('status')}" for name, value in configs.items() if value.get("status") != "ok"]
        return {
            "status": "ok" if not warnings else "degraded",
            "service": "validation_gate",
            "enabled": True,
            "deterministic_only": True,
            "report_quality_gate_enabled": True,
            "side_effect_validation_enabled": True,
            "evidence_compliance_enabled": True,
            "context_usage_validation_enabled": True,
            "write_enabled": False,
            "patch_enabled": False,
            "shell_enabled": False,
            "governed_write_enabled": True,
            "governed_patch_apply_enabled": True,
            "governed_shell_enabled": True,
            "direct_side_effects_enabled": False,
            "git_write_enabled": False,
            "rag_enabled": False,
            "memory_write_enabled": False,
            "model_tool_calling_enabled": False,
            "configs": configs,
            "warnings": warnings,
        }
