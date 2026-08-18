from __future__ import annotations

from aipinho.services.debugger.inspectors._shared import BaseInspector, finding, to_dict
from aipinho.services.roles.role_model_run_store import RoleModelRunStore


class ModelRunInspector(BaseInspector):
    target_type = "model_run"

    def inspect(self, run_id: str):
        run = RoleModelRunStore().get(run_id)
        if run is None:
            return self.missing(run_id)
        result = run.result
        data = to_dict(result)
        findings = []
        model_id = str(data.get("selected_model_id") or "")
        if "14b" in model_id.lower() and not data.get("manual_escalation_used"):
            findings.append(finding("auto_selected_14b", "14B model appears without manual escalation trace"))
        if not data.get("evaluation"):
            findings.append(finding("model_run_without_evaluation", "Model run has no output evaluation"))
        if data.get("fallback_used") and not data.get("fallback_model_id"):
            findings.append(finding("fallback_used_without_model", "Fallback used without fallback_model_id"))
        if not data.get("trace_id"):
            findings.append(finding("model_run_without_trace", "Model run has no trace_id", "high"))
        return self.result(run_id, {"run": data, "request": run.request, "prompt_contract": run.prompt_contract}, findings, summary=f"Model {model_id or 'unknown'} inspected")
