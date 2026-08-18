from __future__ import annotations

from aipinho.services.debugger.inspectors._shared import BaseInspector, finding, to_dict
from aipinho.services.roles.role_model_binding_service import RoleModelBindingService
from aipinho.services.roles.role_model_run_store import RoleModelRunStore


class RoleRunInspector(BaseInspector):
    target_type = "role_run"

    def inspect(self, run_id: str):
        run = RoleModelRunStore().get(run_id)
        if run is None:
            return self.missing(run_id)
        data = to_dict(run.result)
        binding = RoleModelBindingService().get_binding(str(data.get("role_id") or ""))
        findings = []
        if binding is None:
            findings.append(finding("role_binding_missing", "Role run has no binding"))
        if not run.prompt_contract:
            findings.append(finding("prompt_contract_missing", "Role run has no prompt contract", "high"))
        if not data.get("evaluation"):
            findings.append(finding("role_output_evaluation_missing", "Role output evaluation missing"))
        return self.result(run_id, {"run": data, "binding": binding.model_dump() if binding else None, "prompt_contract": run.prompt_contract}, findings, summary="Role run inspected")
