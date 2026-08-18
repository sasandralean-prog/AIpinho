from __future__ import annotations

from typing import Any

from aipinho.core.paths import PATHS
from aipinho.services.validation.side_effect_validator import SideEffectValidator
from aipinho.services.validation.validation_common import as_dict, finding
from aipinho.utils.yaml_loader import load_yaml_file


class RolePipelineValidator:
    def __init__(self) -> None:
        self.side_effects = SideEffectValidator()
        self.policy = load_yaml_file(
            PATHS.config_root / "roles" / "role_pipeline_policy.yaml",
            critical=True,
            root=PATHS.config_root / "roles",
        )

    def validate(self, run: Any) -> list:
        data = as_dict(run)
        findings = []
        if data.get("status") not in {"completed", "partial", "failed", "rejected", "degraded", "needs_input", "preview"}:
            findings.append(finding("status_inconsistency", "Unknown role pipeline status", "RolePipelineRun status is not recognized.", severity="error", validator="role_pipeline", blocking=True))
        if data.get("status") == "completed" and not data.get("passes"):
            findings.append(finding("empty_output", "Role pipeline has no passes", "Completed RolePipelineRun requires passes.", severity="error", validator="role_pipeline", blocking=True))

        reject_real = self._reject_real_inference()
        for item in data.get("passes", []) or []:
            role_pass = as_dict(item)
            if role_pass.get("required", True) and role_pass.get("status") not in {"completed"}:
                findings.append(finding("required_role_pass_not_completed", "Required role pass did not complete", "Required RolePass must complete for a trusted completed pipeline.", severity="error", validator="role_pipeline", evidence=[str(role_pass.get("pass_id"))], blocking=True))
            if not role_pass.get("evaluation_result"):
                findings.append(finding("missing_evaluation", "Role pass missing evaluation", "RolePass requires evaluation_result before output can be trusted.", severity="error", validator="role_pipeline", evidence=[str(role_pass.get("pass_id"))], blocking=True))
            eval_status = role_pass.get("evaluation_result", {}).get("status") if isinstance(role_pass.get("evaluation_result"), dict) else None
            if eval_status in {"rejected", "needs_retry", "degraded"}:
                findings.append(finding("role_pass_evaluation_failed", "Role pass evaluation failed", "RolePass evaluation status is not accepted.", severity="error", validator="role_pipeline", evidence=[str(eval_status)], blocking=True))
            if reject_real and role_pass.get("model_response", {}).get("real_inference") is True:
                findings.append(finding("real_inference_auto_use", "Real inference signal", "RolePipelineRun cannot auto-use real inference under current policy.", severity="critical", validator="role_pipeline", blocking=True))

        final_output = data.get("final_output") or {}
        if isinstance(final_output, dict):
            for key in ("side_effects", "tools", "write", "patch"):
                if final_output.get(key) is True:
                    findings.append(finding("side_effect_violation", "Role pipeline unsafe output flag", f"final_output.{key}=true", severity="critical", validator="role_pipeline", blocking=True))
        findings.extend(self.side_effects.validate(data))
        return findings

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "role_pipeline_validator", "real_inference_auto_use": not self._reject_real_inference()}

    def _reject_real_inference(self) -> bool:
        validation_policy = self.policy.get("validation_integration", {}) if isinstance(self.policy.get("validation_integration", {}), dict) else {}
        return bool(validation_policy.get("reject_real_inference_auto_use", False))
