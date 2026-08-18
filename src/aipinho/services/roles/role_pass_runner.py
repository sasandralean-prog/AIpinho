from __future__ import annotations

from aipinho.schemas.roles.role_model_gate import RoleModelGateRequest
from aipinho.schemas.roles.role_pass import RolePass
from aipinho.schemas.roles.role_pass_input import RolePassInput
from aipinho.schemas.roles.role_pass_output import RolePassOutput
from aipinho.schemas.roles.role_policy import RolePolicyRequest
from aipinho.services.evaluation.model_response_evaluator import ModelResponseEvaluator
from aipinho.services.models.model_invocation_service import ModelInvocationService
from aipinho.services.roles.effective_role_policy_service import EffectiveRolePolicyService
from aipinho.services.roles.role_fallback_service import RoleFallbackService
from aipinho.services.roles.role_model_gate_service import RoleModelGateService
from aipinho.services.roles.role_output_validator import RoleOutputValidator
from aipinho.services.roles.role_prompt_service import RolePromptService


class RolePassRunner:
    def __init__(
        self,
        effective_policy: EffectiveRolePolicyService | None = None,
        prompt_service: RolePromptService | None = None,
        model_gate: RoleModelGateService | None = None,
        model_invocation: ModelInvocationService | None = None,
        output_validator: RoleOutputValidator | None = None,
        fallback_service: RoleFallbackService | None = None,
    ) -> None:
        self.effective_policy = effective_policy or EffectiveRolePolicyService()
        self.prompt_service = prompt_service or RolePromptService()
        self.model_gate = model_gate or RoleModelGateService()
        self.model_invocation = model_invocation or ModelInvocationService()
        self.output_validator = output_validator or RoleOutputValidator()
        self.fallback_service = fallback_service or RoleFallbackService()

    def preview(self, role_input: RolePassInput) -> RolePass:
        role_pass = RolePass(pass_id=role_input.pass_id, role_id=role_input.role_id, required=role_input.required, input=role_input.model_dump(exclude={"user_message"}))
        effective = self.effective_policy.resolve(self._policy_request(role_input))
        role_pass.effective_policy = effective
        if not effective.allowed:
            role_pass.mark_finished("rejected" if role_input.required else "skipped")
            role_pass.warnings.extend(effective.blocked_reasons)
            return role_pass
        preview = self.prompt_service.preview(role_input, effective)
        role_pass.prompt_assembly = preview.assembly.model_dump(exclude={"messages"})
        model_policy = "binding_controlled" if role_input.model_mode == "manual_real" else effective.model_policy
        gate = self.model_gate.decide(RoleModelGateRequest(role_id=role_input.role_id, model_policy=model_policy, requested_model_id=role_input.requested_model_id, purpose=role_input.purpose, prompt_assembly=role_pass.prompt_assembly, output_contract=preview.assembly.output_contract.model_dump(), safety_envelope=preview.assembly.safety_envelope.model_dump(), allow_real_inference=role_input.allow_real_inference, operator_confirmed=role_input.operator_confirmed))
        role_pass.model_gate = gate
        role_pass.mark_finished("degraded" if not gate.allowed and gate.status != "deterministic_only" else "completed")
        role_pass.trace.extend([*effective.trace, *gate.trace, {"stage": "role_pass_preview", "status": role_pass.status, "reason": "no_model_invocation"}])
        return role_pass

    def run(self, role_input: RolePassInput) -> RolePass:
        role_pass = RolePass(pass_id=role_input.pass_id, role_id=role_input.role_id, required=role_input.required, input=role_input.model_dump(exclude={"user_message"}))
        role_pass.mark_started()
        effective = self.effective_policy.resolve(self._policy_request(role_input))
        role_pass.effective_policy = effective
        if not effective.allowed:
            fb = self.fallback_service.skip_optional_pass(",".join(effective.blocked_reasons)) if not role_input.required else self.fallback_service.speaker_safe_error(",".join(effective.blocked_reasons))
            role_pass.output = RolePassOutput(role_id=role_input.role_id, status="skipped" if fb.skip_pass else "rejected", content=fb.message, source="fallback", warnings=effective.blocked_reasons)
            role_pass.warnings.extend(effective.blocked_reasons)
            role_pass.mark_finished("skipped" if fb.skip_pass else "rejected")
            role_pass.trace.extend(effective.trace)
            return role_pass
        preview = self.prompt_service.preview(role_input, effective)
        role_pass.prompt_assembly = preview.assembly.model_dump(exclude={"messages"})
        model_policy = "binding_controlled" if role_input.model_mode == "manual_real" else effective.model_policy
        gate = self.model_gate.decide(RoleModelGateRequest(role_id=role_input.role_id, model_policy=model_policy, requested_model_id=role_input.requested_model_id, purpose=role_input.purpose, prompt_assembly=role_pass.prompt_assembly, output_contract=preview.assembly.output_contract.model_dump(), safety_envelope=preview.assembly.safety_envelope.model_dump(), allow_real_inference=role_input.allow_real_inference, operator_confirmed=role_input.operator_confirmed))
        role_pass.model_gate = gate
        if gate.status == "deterministic_only":
            fb = self.fallback_service.deterministic_output(role_input.role_id)
            output = RolePassOutput(role_id=role_input.role_id, status="completed", content=fb.message, source="deterministic")
            validation = self.output_validator.validate(output, output_contract=preview.assembly.output_contract.model_dump(), safety_envelope=preview.assembly.safety_envelope.model_dump(), evidence=role_input.evidence, policy_decision=role_input.policy_decision)
            role_pass.output = output
            role_pass.evaluation_result = {"status": "accepted" if validation["valid"] else "rejected", "violations": validation["violations"], "warnings": validation["warnings"]}
            role_pass.mark_finished("completed" if validation["valid"] else "rejected")
            role_pass.warnings.extend(validation["warnings"])
            role_pass.trace.extend([*effective.trace, *gate.trace, {"stage": "deterministic_output", "status": role_pass.status}])
            return role_pass
        if not gate.allowed:
            fb = self.fallback_service.speaker_safe_error(",".join(gate.blocked_reasons))
            role_pass.output = RolePassOutput(role_id=role_input.role_id, status="rejected", content=fb.message, source="fallback", warnings=gate.blocked_reasons)
            role_pass.mark_finished("rejected")
            role_pass.warnings.extend(gate.blocked_reasons)
            role_pass.trace.extend([*effective.trace, *gate.trace])
            return role_pass
        model_request = preview.model_request.model_copy(deep=True)
        model_request.metadata = {
            **model_request.metadata,
            "evidence_context": role_input.evidence,
            "tool_results": None,
            "artifact_results": None,
            "patch_results": None,
            "allow_real_inference": role_input.allow_real_inference,
            "operator_confirmed": role_input.operator_confirmed,
            "role_pipeline_controlled_inference": role_input.model_mode == "manual_real",
            "auto_role_pipeline_inference": role_input.model_mode == "manual_real",
        }
        response = self.model_invocation.invoke(model_request)
        role_pass.model_response = response.model_dump(exclude={"content"})
        evaluation = response.evaluation_result or {"status": "accepted" if response.status == "completed" else "degraded", "violations": response.warnings, "warnings": response.warnings}
        role_pass.evaluation_result = evaluation
        output = RolePassOutput(role_id=role_input.role_id, status="completed", content=response.content, structured_output=response.structured_output or {}, source="stub" if not response.real_inference else "model_evaluated", evaluation_status=str(evaluation.get("status")), warnings=list(response.warnings), violations=[str(item) for item in evaluation.get("violations", [])] if isinstance(evaluation, dict) else [])
        validation = self.output_validator.validate(output, output_contract=preview.assembly.output_contract.model_dump(), safety_envelope=preview.assembly.safety_envelope.model_dump(), evidence=role_input.evidence, policy_decision=role_input.policy_decision)
        if response.status != "completed" or evaluation.get("status") in {"rejected", "needs_retry", "degraded"} or not validation["valid"]:
            output.status = "rejected"
            output.violations = list(dict.fromkeys([*output.violations, *validation["violations"]]))
            output.warnings = list(dict.fromkeys([*output.warnings, *validation["warnings"]]))
            role_pass.status = "rejected"
        else:
            output.status = "completed"
            role_pass.status = "completed"
        role_pass.output = output
        role_pass.warnings.extend(output.warnings)
        role_pass.trace.extend([*effective.trace, *gate.trace, *response.trace, {"stage": "role_output_validator", "status": "ok" if validation["valid"] else "rejected", "reason": ",".join(validation["violations"])}])
        role_pass.mark_finished(role_pass.status)  # type: ignore[arg-type]
        return role_pass

    def _policy_request(self, role_input: RolePassInput) -> RolePolicyRequest:
        return RolePolicyRequest(role_id=role_input.role_id, intent_map=role_input.intent_map, policy_decision=role_input.policy_decision, task_contract=role_input.task_contract, pipeline_context={"pass_id": role_input.pass_id})

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "role_pass_runner", "tools_enabled": False, "write_enabled": False, "patch_enabled": False, "model_response_evaluation": ModelResponseEvaluator().status()}
