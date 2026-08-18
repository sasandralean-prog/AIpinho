from __future__ import annotations

from aipinho.adapters.llm_providers.stub_provider import StubProvider
from aipinho.schemas.evaluation.evaluation_request import EvaluationRequest
from aipinho.schemas.models.model_request import ModelRequest
from aipinho.schemas.models.model_response import ModelResponse, ModelUsage
from aipinho.schemas.prompts.prompt_message import PromptMessage
from aipinho.services.evaluation.model_response_evaluator import ModelResponseEvaluator
from aipinho.services.models.inference_runtime_service import InferenceRuntimeService
from aipinho.services.models.model_router_service import ModelRouterService
from aipinho.services.prompts.output_contract_builder import OutputContractBuilder


class ModelInvocationService:
    def __init__(
        self,
        router: ModelRouterService | None = None,
        output_contract_builder: OutputContractBuilder | None = None,
        evaluator: ModelResponseEvaluator | None = None,
        inference_runtime: InferenceRuntimeService | None = None,
    ) -> None:
        self.router = router or ModelRouterService()
        self.output_contract_builder = output_contract_builder or OutputContractBuilder()
        self.evaluator = evaluator or ModelResponseEvaluator()
        self.stub = StubProvider()
        self.inference_runtime = inference_runtime or InferenceRuntimeService()

    def invoke(self, request: ModelRequest) -> ModelResponse:
        if request.provider_id == "stub.local" and request.model_id == "stub.default":
            return self._evaluate_response(self.stub.invoke(request), request)
        if self._manual_real_chat_requested(request):
            return self._evaluate_response(self.inference_runtime.invoke(request), request)
        decision = self.router.select_model(
            requested_model_id=request.model_id,
            purpose=str(request.metadata.get("purpose", "chat")),
            role_id=str(request.metadata.get("role_id", "speaker")),
        )
        if decision.status != "ok" or decision.model is None or decision.provider is None:
            return ModelResponse(
                request_id=request.request_id,
                model_id=decision.model.model_id if decision.model else request.model_id,
                provider_id=decision.provider.provider_id if decision.provider else request.provider_id,
                status="blocked",
                content=f"Model invocation blocked: {decision.reason}",
                usage=ModelUsage(),
                finish_reason="blocked",
                real_inference=False,
                warnings=[decision.reason, *decision.warnings],
                trace=[decision.as_dict()],
            )
        request = request.model_copy(update={"model_id": decision.model.model_id, "provider_id": decision.provider.provider_id})
        if decision.provider.type == "llama_cpp" or decision.provider.type.startswith("llama_cpp_"):
            return self._evaluate_response(self.inference_runtime.invoke(request), request)
        if decision.provider.type != "stub":
            return ModelResponse(
                request_id=request.request_id,
                model_id=request.model_id,
                provider_id=request.provider_id,
                status="blocked",
                content="Only stub and gated llama.cpp providers are registered for invocation.",
                usage=ModelUsage(),
                finish_reason="blocked",
                real_inference=False,
                warnings=["provider_not_supported"],
            )
        return self._evaluate_response(self.stub.invoke(request), request)

    def invoke_role_model(self, request: ModelRequest) -> ModelResponse:
        provider_id = request.provider_id
        provider = self.inference_runtime.provider_registry.get_provider(provider_id)
        provider_type = provider.type if provider is not None else ""
        if provider_type != "llama_cpp_text":
            return ModelResponse(
                request_id=request.request_id,
                model_id=request.model_id,
                provider_id=provider_id,
                status="blocked",
                content="Role model invocation blocked: provider is not a governed text inference provider.",
                usage=ModelUsage(input_chars=sum(len(message.content) for message in request.messages)),
                finish_reason="blocked",
                real_inference=False,
                warnings=["provider_runtime_not_text_inference"],
                trace=[{"stage": "role_model_invocation", "status": "blocked", "reason": "provider_runtime_not_text_inference"}],
            )
        return self._evaluate_response(self.inference_runtime.invoke(request), request)

    def _manual_real_chat_requested(self, request: ModelRequest) -> bool:
        return (
            request.provider_id == "llama_cpp.local"
            and bool(request.metadata.get("manual_mode", False))
            and bool(request.metadata.get("chat_manual_inference", False))
            and bool(request.metadata.get("allow_real_inference", False))
            and bool(request.metadata.get("operator_confirmed", False))
        )

    def _evaluate_response(self, response: ModelResponse, request: ModelRequest) -> ModelResponse:
        purpose = str(request.metadata.get("purpose", "chat"))
        evidence_context = request.metadata.get("evidence_context", [])
        if not isinstance(evidence_context, list):
            evidence_context = []
        evaluation = self.evaluator.evaluate(
            EvaluationRequest(
                model_response=response.model_dump(exclude={"evaluation_result"}),
                model_request=request.model_dump(),
                output_contract=request.output_contract,
                safety_envelope=request.safety_envelope,
                evidence_context=evidence_context,
                policy_decision={"tool_results": request.metadata.get("tool_results"), "artifact_results": request.metadata.get("artifact_results"), "patch_results": request.metadata.get("patch_results")},
                purpose=purpose if purpose in {"chat", "project_report", "code_analysis", "task_preview", "smoke_test"} else "chat",
                include_trace=bool(request.metadata.get("include_evaluation_trace", False)),
            )
        )
        response.evaluation_result = evaluation.model_dump()
        response.metadata = {**response.metadata, "evaluation_status": evaluation.status, "evaluation_score": evaluation.score, "fallback_decision": evaluation.fallback_decision.model_dump()}
        if evaluation.status in {"rejected", "needs_retry", "degraded"} and response.status == "completed":
            response.status = "degraded"
            response.warnings = list(dict.fromkeys([*response.warnings, "model_response_evaluation_failed", *evaluation.violations, *evaluation.warnings]))
            response.trace.append({"stage": "model_response_evaluation", "status": evaluation.status, "reason": ",".join(evaluation.violations)})
        elif evaluation.status == "accepted_with_warnings":
            response.warnings = list(dict.fromkeys([*response.warnings, *evaluation.warnings]))
            response.trace.append({"stage": "model_response_evaluation", "status": evaluation.status, "reason": ",".join(evaluation.warnings)})
        else:
            response.trace.append({"stage": "model_response_evaluation", "status": evaluation.status})
        return response

    def invoke_stub_prompt(
        self,
        *,
        prompt: str,
        model_id: str = "stub.default",
        output_contract_type: str = "plain_text",
        metadata: dict[str, object] | None = None,
    ) -> ModelResponse:
        contract = self.output_contract_builder.get_contract(output_contract_type)
        request = ModelRequest(
            model_id=model_id,
            provider_id="stub.local",
            messages=[PromptMessage(role="user", content=prompt or "Invoke stub provider.")],
            output_contract=contract.model_dump(),
            safety_envelope={"envelope_id": "chat", "rules": ["no_tools", "no_files", "no_patch", "no_raw_debug"]},
            metadata={"purpose": "chat", "role_id": "speaker", **(metadata or {})},
        )
        return self.invoke(request)

    def status(self) -> dict[str, object]:
        router_status = self.router.status()
        return {
            "status": "ok",
            "service": "model_invocation",
            "real_inference_enabled": bool(router_status.get("real_inference_enabled", False)),
            "controlled_role_inference_enabled": True,
            "router": router_status,
            "provider": self.stub.status(),
            "inference_runtime": self.inference_runtime.status(),
            "evaluation": self.evaluator.status(),
        }
