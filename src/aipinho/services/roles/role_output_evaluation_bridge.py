from __future__ import annotations

from aipinho.schemas.evaluation.evaluation_request import EvaluationRequest
from aipinho.schemas.models.model_response import ModelResponse
from aipinho.schemas.roles.role_model_binding import RoleOutputEvaluation, RolePromptContract
from aipinho.services.evaluation.model_response_evaluator import ModelResponseEvaluator


class RoleOutputEvaluationBridge:
    def __init__(self, evaluator: ModelResponseEvaluator | None = None) -> None:
        self.evaluator = evaluator or ModelResponseEvaluator()

    def evaluate(self, response: ModelResponse, prompt_contract: RolePromptContract, *, include_trace: bool = True) -> RoleOutputEvaluation:
        result = self.evaluator.evaluate(
            EvaluationRequest(
                model_response=response.model_dump(exclude={"evaluation_result"}),
                model_request={"role_id": prompt_contract.role_id, "model_id": prompt_contract.model_id},
                output_contract=prompt_contract.policy_envelope.get("contract", {"contract_type": "plain_text", "format": "text"}),
                safety_envelope=prompt_contract.safety_envelope,
                policy_decision={"role_model": True, "tool_results": None, "patch_results": None, "artifact_results": None},
                purpose="code_analysis",
                include_trace=include_trace,
            )
        )
        accepted = result.status in {"accepted", "accepted_with_warnings"}
        return RoleOutputEvaluation(
            status=result.status,
            accepted=accepted,
            warnings=result.warnings,
            violations=result.violations,
            retry_recommended=bool(result.retry_decision.should_retry),
            fallback_recommended=bool(result.fallback_decision.should_fallback),
            raw=result.model_dump(),
        )

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "role_output_evaluation_bridge"}
