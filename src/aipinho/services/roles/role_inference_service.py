from __future__ import annotations

from datetime import datetime, timezone

from aipinho.schemas.models.generation_config import GenerationConfig
from aipinho.schemas.models.model_request import ModelRequest
from aipinho.schemas.models.model_response import ModelResponse
from aipinho.schemas.roles.role_model_binding import RoleInferenceRequest, RoleInferenceResult, RoleModelRun
from aipinho.services.models.model_invocation_service import ModelInvocationService
from aipinho.services.roles.role_inference_audit_service import RoleInferenceAuditService
from aipinho.services.roles.role_model_binding_service import RoleModelBindingService
from aipinho.services.roles.role_model_fallback_service import RoleModelFallbackService
from aipinho.services.roles.role_model_gate_service_v2 import RoleModelGateServiceV2
from aipinho.services.roles.role_model_run_store import RoleModelRunStore
from aipinho.services.roles.role_model_trace_service import RoleModelTraceService
from aipinho.services.roles.role_output_evaluation_bridge import RoleOutputEvaluationBridge
from aipinho.services.roles.role_prompt_contract_builder import RolePromptContractBuilder
from aipinho.services.roles.role_inference_policy_service import RoleInferencePolicyService


class RoleInferenceService:
    def __init__(
        self,
        bindings: RoleModelBindingService | None = None,
        gate: RoleModelGateServiceV2 | None = None,
        prompt_builder: RolePromptContractBuilder | None = None,
        invoker: ModelInvocationService | None = None,
        evaluator: RoleOutputEvaluationBridge | None = None,
        fallback: RoleModelFallbackService | None = None,
        store: RoleModelRunStore | None = None,
        trace: RoleModelTraceService | None = None,
        audit: RoleInferenceAuditService | None = None,
        policy: RoleInferencePolicyService | None = None,
    ) -> None:
        self.bindings = bindings or RoleModelBindingService()
        self.gate = gate or RoleModelGateServiceV2(binding_service=self.bindings)
        self.prompt_builder = prompt_builder or RolePromptContractBuilder()
        self.invoker = invoker or ModelInvocationService()
        self.evaluator = evaluator or RoleOutputEvaluationBridge()
        self.fallback = fallback or RoleModelFallbackService()
        self.store = store or RoleModelRunStore()
        self.trace = trace or RoleModelTraceService()
        self.audit = audit or RoleInferenceAuditService()
        self.policy = policy or RoleInferencePolicyService()

    def preview(self, role_id: str, request: RoleInferenceRequest | None = None, *, manual: bool = False) -> RoleInferenceResult:
        request = request or RoleInferenceRequest(role_id=role_id)
        gate = self.gate.decide(role_id, request, manual=manual)
        binding = self.bindings.get_binding(role_id)
        prompt_contract = None
        if binding and gate.selected_model_id:
            prompt_contract = self.prompt_builder.build(binding, request, gate.selected_model_id)
            if prompt_contract.blocked_reasons:
                gate.allowed = False
                gate.status = "blocked"
                gate.blocked_reasons = list(dict.fromkeys([*gate.blocked_reasons, *prompt_contract.blocked_reasons]))
        status = "preview" if gate.allowed else gate.status
        result = RoleInferenceResult(
            role_id=role_id,
            status=status,  # type: ignore[arg-type]
            selected_model_id=gate.selected_model_id,
            provider_id=gate.provider_id,
            fallback_model_id=gate.fallback_model_id,
            manual_escalation_used=gate.manual_escalation_used,
            raw_output_hidden=True,
            output="Preview only. No model was invoked.",
            budget=gate.budget,
            warnings=gate.warnings,
            blocked_reasons=gate.blocked_reasons,
            trace_id=gate.trace_id,
            side_effects=False,
            metadata={"prompt_contract": prompt_contract.model_dump() if prompt_contract else {}},
        )
        return result

    def run(self, role_id: str, request: RoleInferenceRequest | None = None, *, manual: bool = False) -> RoleInferenceResult:
        request = request or RoleInferenceRequest(role_id=role_id)
        gate = self.gate.decide(role_id, request, manual=manual)
        binding = self.bindings.get_binding(role_id)
        if not gate.allowed or binding is None or gate.selected_model_id is None:
            result = RoleInferenceResult(
                role_id=role_id,
                status=gate.status,  # type: ignore[arg-type]
                selected_model_id=gate.selected_model_id,
                provider_id=gate.provider_id,
                fallback_model_id=gate.fallback_model_id,
                manual_escalation_used=gate.manual_escalation_used,
                output="Role model run blocked by gate.",
                budget=gate.budget,
                warnings=gate.warnings,
                blocked_reasons=gate.blocked_reasons,
                trace_id=gate.trace_id,
            )
            return self._save(request, result, {})
        prompt_contract = self.prompt_builder.build(binding, request, gate.selected_model_id)
        if prompt_contract.blocked_reasons:
            result = RoleInferenceResult(
                role_id=role_id,
                status="blocked",
                selected_model_id=gate.selected_model_id,
                provider_id=gate.provider_id,
                fallback_model_id=gate.fallback_model_id,
                output="Role prompt contract blocked.",
                budget=gate.budget,
                warnings=gate.warnings,
                blocked_reasons=prompt_contract.blocked_reasons,
                trace_id=gate.trace_id,
            )
            return self._save(request, result, prompt_contract.model_dump())
        max_output_tokens = self._metadata_int(
            request.metadata.get("max_output_tokens"),
            default=int(gate.budget.get("max_output_tokens", 1024)),
            minimum=1,
            maximum=int(gate.budget.get("max_output_tokens", 1024)),
        )
        timeout_seconds = self._metadata_int(
            request.metadata.get("timeout_seconds"),
            default=int(gate.budget.get("timeout_seconds", 90)),
            minimum=1,
            maximum=int(gate.budget.get("timeout_seconds", 90)),
        )
        runtime_metadata = {
            key: request.metadata[key]
            for key in ("ctx_size", "max_stdout_chars", "max_stderr_chars")
            if key in request.metadata
        }
        patch_candidate = request.context.get("patch_candidate") if isinstance(request.context.get("patch_candidate"), dict) else {}
        model_request = ModelRequest(
            model_id=gate.selected_model_id,
            provider_id=gate.provider_id or "llama_cpp_text",
            messages=self.prompt_builder.messages(prompt_contract),
            generation_config=GenerationConfig(max_tokens=max_output_tokens),
            output_contract=prompt_contract.policy_envelope.get("contract", {"contract_type": "plain_text", "format": "text"}),
            safety_envelope=prompt_contract.safety_envelope,
            metadata={
                "purpose": "code_analysis",
                "role_id": role_id,
                "operation_type": "role_inference",
                "semantic_goal": request.prompt,
                "prompt_original": request.prompt,
                "role_context": request.context,
                "patch_candidate": patch_candidate,
                "context_budget": gate.budget,
                "role_model_run": True,
                "allow_real_inference": True,
                "manual_mode": True,
                "operator_confirmed": request.operator_confirmed or not request.manual_escalation,
                "timeout_seconds": timeout_seconds,
                "include_evaluation_trace": request.include_trace,
                **runtime_metadata,
            },
        )
        model_response = self.invoker.invoke_role_model(model_request)
        evaluation = self.evaluator.evaluate(model_response, prompt_contract, include_trace=request.include_trace)
        final_response: ModelResponse = model_response
        fallback_used = False
        status = "completed" if evaluation.accepted and model_response.status == "completed" else "degraded"
        if model_response.status != "completed" or not evaluation.accepted:
            fallback_decision = self.fallback.decide(binding, reason=model_response.status if model_response.status != "completed" else evaluation.status)
            if fallback_decision.fallback_allowed:
                final_response = self.fallback.deterministic_response(request_id=model_request.request_id, role_id=role_id, fallback_model_id=fallback_decision.fallback_model_id, reason=fallback_decision.reason or "primary_unaccepted")
                evaluation = self.evaluator.evaluate(final_response, prompt_contract, include_trace=request.include_trace)
                fallback_used = True
                status = "fallback_used" if evaluation.accepted else "rejected"
        result = RoleInferenceResult(
            role_id=role_id,
            status=status,  # type: ignore[arg-type]
            selected_model_id=gate.selected_model_id,
            provider_id=gate.provider_id,
            fallback_model_id=gate.fallback_model_id,
            fallback_used=fallback_used,
            manual_escalation_used=gate.manual_escalation_used,
            raw_output_hidden=True,
            output=final_response.content if evaluation.accepted or fallback_used else "",
            evaluation=evaluation.model_dump(),
            budget=gate.budget,
            warnings=list(dict.fromkeys([*gate.warnings, *final_response.warnings, *evaluation.warnings])),
            blocked_reasons=list(dict.fromkeys([*gate.blocked_reasons, *evaluation.violations])),
            trace_id=gate.trace_id,
            model_response_status=model_response.status,
            real_inference_attempted=True,
            real_inference_completed=bool(model_response.real_inference and model_response.status == "completed"),
            side_effects=False,
            finished_at=datetime.now(timezone.utc).isoformat(),
            metadata={
                "inference_runtime": final_response.metadata.get("inference_runtime", {}),
                "canonical_inference_input_artifact": final_response.metadata.get("canonical_inference_input_artifact", {}),
                "canonical_inference_output_artifact": final_response.metadata.get("canonical_inference_output_artifact", {}),
                "inference_input_doctor": final_response.metadata.get("inference_input_doctor", {}),
            },
        )
        self.trace.record(gate.trace_id, role_id=role_id, event_type="role_model_run_complete", status=result.status, summary="Role model run completed", model_id=gate.selected_model_id, data=result.model_dump())
        return self._save(request, result, prompt_contract.model_dump())

    def _save(self, request: RoleInferenceRequest, result: RoleInferenceResult, prompt_contract: dict[str, object]) -> RoleInferenceResult:
        run = RoleModelRun(result=result, request=request.model_dump(), prompt_contract=prompt_contract)
        self.store.save(run)
        self.audit.record({"run_id": result.run_id, "role_id": result.role_id, "status": result.status, "model_id": result.selected_model_id, "fallback_used": result.fallback_used, "side_effects": False})
        return result

    def _metadata_int(self, value: object, *, default: int, minimum: int, maximum: int) -> int:
        try:
            parsed = int(value) if value is not None else int(default)
        except (TypeError, ValueError):
            parsed = int(default)
        return max(minimum, min(maximum, parsed))

    def get_run(self, run_id: str) -> RoleModelRun | None:
        return self.store.get(run_id)

    def list_runs(self, *, role_id: str | None = None, status: str | None = None, model_id: str | None = None):
        return self.store.list_runs(role_id=role_id, status=status, model_id=model_id)

    def status(self) -> dict[str, object]:
        policy_status = self.policy.status()
        return {
            "status": "ok",
            "service": "role_inference",
            "chat_auto_role_inference": bool(policy_status.get("chat_auto_role_inference", False)),
            "policy": policy_status,
            "runs": self.store.status().get("runs", 0),
        }
