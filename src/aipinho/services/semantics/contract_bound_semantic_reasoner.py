from __future__ import annotations

import json
from typing import Any

from aipinho.schemas.models.model_request import ModelRequest
from aipinho.schemas.prompts.prompt_message import PromptMessage
from aipinho.schemas.roles.role_model_binding import RoleInferenceRequest
from aipinho.services.models.model_invocation_service import ModelInvocationService
from aipinho.services.models.model_router_service import ModelRouterService
from aipinho.services.roles.role_inference_budget_service import (
    RoleInferenceBudgetService,
)
from aipinho.services.roles.role_model_binding_service import (
    RoleModelBindingService,
)
from aipinho.services.roles.role_model_fallback_service import (
    RoleModelFallbackService,
)


class ContractBoundSemanticReasoner:
    """Model-assisted semantic proposal boundary.

    Model output is never authority. Callers must validate every candidate
    against deterministic contracts before materializing a decision.
    """

    def __init__(
        self,
        *,
        router: ModelRouterService | None = None,
        invocation: ModelInvocationService | None = None,
        bindings: RoleModelBindingService | None = None,
        budgets: RoleInferenceBudgetService | None = None,
        fallback: RoleModelFallbackService | None = None,
        timeout_seconds: int | None = None,
    ) -> None:
        self.router = router or ModelRouterService()
        self.invocation = invocation or ModelInvocationService(router=self.router)
        self.bindings = bindings or RoleModelBindingService()
        self.budgets = budgets or RoleInferenceBudgetService()
        self.fallback = fallback or RoleModelFallbackService()
        self.timeout_seconds = (
            max(1, int(timeout_seconds))
            if timeout_seconds is not None
            else None
        )

    def propose_json(
        self,
        *,
        semantic_goal: str,
        payload: dict[str, Any],
        allowed_fields: list[str],
        required_fields: list[str],
        role_id: str = "semantic_interpreter",
        max_tokens: int = 700,
    ) -> dict[str, Any]:
        binding = self.bindings.resolve_binding(role_id)
        if binding is None or not binding.enabled:
            return {
                "status": "unavailable",
                "reason_code": "SEMANTIC_REASONER_ROLE_BINDING_UNAVAILABLE",
                "role_id": role_id,
            }
        decision = self.router.select_model(purpose="chat", role_id=role_id)
        if decision.status != "ok" or decision.model is None or decision.provider is None:
            return {
                "status": "unavailable",
                "reason_code": "SEMANTIC_REASONER_MODEL_UNAVAILABLE",
                "route": decision.as_dict(),
            }
        system = (
            "You are a semantic interpretation component inside a governed system. "
            "Return JSON only. You propose semantic candidates; you do not authorize "
            "execution, permissions, truth claims, or state transitions. Never invent "
            "evidence. Use only the supplied payload and allowed vocabulary."
        )
        user = json.dumps(
            {
                "semantic_goal": semantic_goal,
                "allowed_fields": allowed_fields,
                "required_fields": required_fields,
                "payload": payload,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
        role_budget = self.budgets.calculate(
            binding,
            RoleInferenceRequest(
                role_id=role_id,
                prompt=user,
                context={"semantic_goal": semantic_goal},
            ),
            hardware_class=getattr(
                decision.model,
                "hardware_class",
                None,
            ),
        )
        if role_budget.exceeded:
            return {
                "status": "unavailable",
                "reason_code": "SEMANTIC_REASONER_ROLE_BUDGET_EXCEEDED",
                "role_id": role_id,
                "warnings": list(role_budget.warnings),
                "role_budget": role_budget.model_dump(mode="json"),
            }
        effective_timeout = (
            self.timeout_seconds
            if self.timeout_seconds is not None
            else role_budget.timeout_seconds
        )
        effective_max_tokens = max(
            1,
            min(int(max_tokens), int(role_budget.max_output_tokens)),
        )
        request = ModelRequest(
            model_id=decision.model.model_id,
            provider_id=decision.provider.provider_id,
            messages=[
                PromptMessage(role="system", content=system),
                PromptMessage(role="user", content=user),
            ],
            output_contract={
                "contract_type": "json",
                "format": "json",
                "require_valid_json": True,
                "required_fields": required_fields,
                "json_shape": payload.get("output_schema"),
            },
            safety_envelope={
                "envelope_id": "semantic_reasoning_readonly",
                "rules": ["no_tools", "no_files", "no_patch", "no_side_effects", "candidate_only"],
            },
            metadata={
                "purpose": "chat",
                "role_id": role_id,
                "role_pipeline_controlled_inference": True,
                "semantic_reasoner_controlled_inference": True,
                "semantic_goal": semantic_goal,
                "max_stdout_chars": 12000,
                "timeout_seconds": effective_timeout,
                "role_budget": role_budget.model_dump(mode="json"),
            },
        )
        request.generation_config.max_tokens = effective_max_tokens
        response, retry_attempts, retry_warnings = (
            self._invoke_with_governed_retry(request)
        )
        primary_model_id = response.model_id
        fallback_used = False
        fallback_model_id = None
        fallback_retry_attempts = 0
        fallback_warnings: list[str] = []
        fallback_reason = self._fallback_reason(
            response,
            required_fields=required_fields,
        )
        if fallback_reason:
            fallback_decision = self.fallback.decide(
                binding,
                reason=fallback_reason,
                attempt=0,
                enforce_runtime_policy=True,
            )
            if (
                fallback_decision.fallback_allowed
                and fallback_decision.fallback_model_id
            ):
                fallback_route = self.router.select_model(
                    requested_model_id=(
                        fallback_decision.fallback_model_id
                    ),
                    purpose="chat",
                    role_id=role_id,
                )
                if (
                    fallback_route.status == "ok"
                    and fallback_route.model is not None
                    and fallback_route.provider is not None
                ):
                    fallback_request = request.model_copy(
                        update={
                            "model_id": fallback_route.model.model_id,
                            "provider_id": (
                                fallback_route.provider.provider_id
                            ),
                            "metadata": {
                                **dict(request.metadata),
                                "semantic_model_fallback": True,
                                "semantic_primary_model_id": (
                                    primary_model_id
                                ),
                                "semantic_fallback_reason": (
                                    fallback_reason
                                ),
                                "semantic_fallback_model_id": (
                                    fallback_route.model.model_id
                                ),
                            },
                        },
                        deep=True,
                    )
                    (
                        response,
                        fallback_retry_attempts,
                        fallback_retry_warnings,
                    ) = self._invoke_with_governed_retry(
                        fallback_request
                    )
                    fallback_used = True
                    fallback_model_id = fallback_route.model.model_id
                    fallback_warnings.extend(
                        fallback_retry_warnings
                    )
                else:
                    fallback_warnings.extend(
                        [
                            "semantic_fallback_route_unavailable",
                            *list(fallback_route.warnings or []),
                        ]
                    )
            else:
                fallback_warnings.extend(
                    fallback_decision.blocked_reasons
                )
        warnings = list(
            dict.fromkeys(
                [
                    *retry_warnings,
                    *fallback_warnings,
                    *response.warnings,
                    *(
                        ["semantic_model_fallback_used"]
                        if fallback_used
                        else []
                    ),
                ]
            )
        )
        total_retry_attempts = (
            retry_attempts + fallback_retry_attempts
        )
        final_evaluation_status = str(
            (
                dict(response.evaluation_result or {})
                if isinstance(response.evaluation_result, dict)
                else {}
            ).get("status")
            or ""
        ).strip()
        if response.status not in {"completed", "degraded"}:
            return {
                "status": "unavailable",
                "reason_code": "SEMANTIC_REASONER_INVOCATION_UNAVAILABLE",
                "model_id": response.model_id,
                "response_id": response.response_id,
                "warnings": warnings,
                "retry_attempts": total_retry_attempts,
                "primary_model_id": primary_model_id,
                "fallback_used": fallback_used,
                "fallback_model_id": fallback_model_id,
            }
        if final_evaluation_status in {"needs_retry", "rejected"}:
            return {
                "status": "invalid",
                "reason_code": (
                    "SEMANTIC_REASONER_EVALUATION_NOT_ACCEPTED"
                ),
                "model_id": response.model_id,
                "response_id": response.response_id,
                "real_inference": response.real_inference,
                "evaluation_status": final_evaluation_status,
                "warnings": warnings,
                "retry_attempts": total_retry_attempts,
                "primary_model_id": primary_model_id,
                "fallback_used": fallback_used,
                "fallback_model_id": fallback_model_id,
            }
        parsed = self._parse_json_object(
            response.content,
            required_fields=required_fields,
        )
        if parsed is None:
            return {
                "status": "invalid",
                "reason_code": "SEMANTIC_REASONER_INVALID_JSON",
                "model_id": response.model_id,
                "response_id": response.response_id,
                "real_inference": response.real_inference,
                "evaluation_status": (response.evaluation_result or {}).get("status"),
                "warnings": warnings,
                "retry_attempts": total_retry_attempts,
                "primary_model_id": primary_model_id,
                "fallback_used": fallback_used,
                "fallback_model_id": fallback_model_id,
            }
        if not isinstance(parsed, dict):
            return {
                "status": "invalid",
                "reason_code": "SEMANTIC_REASONER_OBJECT_REQUIRED",
                "model_id": response.model_id,
                "response_id": response.response_id,
            }
        sanitized = {key: parsed.get(key) for key in allowed_fields if key in parsed}
        missing = [key for key in required_fields if key not in sanitized]
        if missing:
            return {
                "status": "invalid",
                "reason_code": "SEMANTIC_REASONER_REQUIRED_FIELDS_MISSING",
                "missing_fields": missing,
                "model_id": response.model_id,
                "response_id": response.response_id,
            }
        return {
            "status": "candidate",
            "candidate": sanitized,
            "model_id": response.model_id,
            "response_id": response.response_id,
            "real_inference": response.real_inference,
            "evaluation_status": (response.evaluation_result or {}).get("status"),
            "warnings": warnings,
            "retry_attempts": total_retry_attempts,
            "primary_model_id": primary_model_id,
            "fallback_used": fallback_used,
            "fallback_model_id": fallback_model_id,
        }

    def _fallback_reason(
        self,
        response,
        *,
        required_fields: list[str],
    ) -> str | None:
        evaluation = (
            dict(response.evaluation_result or {})
            if isinstance(response.evaluation_result, dict)
            else {}
        )
        evaluation_status = str(
            evaluation.get("status") or ""
        ).strip()
        if evaluation_status in {"needs_retry", "rejected"}:
            return evaluation_status
        if response.status not in {"completed", "degraded"}:
            return str(response.status)
        parsed = self._parse_json_object(
            response.content,
            required_fields=required_fields,
        )
        if parsed is None:
            return (
                "degraded"
                if response.status == "degraded"
                else "rejected"
            )
        return None

    def _invoke_with_governed_retry(
        self,
        request: ModelRequest,
    ):
        response = self.invocation.invoke_role_model(request)
        attempts = 0
        warnings: list[str] = []
        while True:
            evaluation = (
                dict(response.evaluation_result or {})
                if isinstance(response.evaluation_result, dict)
                else {}
            )
            retry = evaluation.get("retry_decision")
            retry = dict(retry) if isinstance(retry, dict) else {}
            should_retry = bool(retry.get("should_retry"))
            max_retries = max(
                0,
                int(retry.get("max_retries", 0) or 0),
            )
            if not should_retry or attempts >= max_retries:
                return response, attempts, warnings

            hint = str(
                retry.get("retry_prompt_hint")
                or "Retry with stricter output contract compliance."
            ).strip()
            contract_violations = [
                str(item)
                for item in list(evaluation.get("violations") or [])
                if str(item)
            ][:8]
            violation_hint = (
                " Observed contract violations: "
                + ", ".join(contract_violations)
                + "."
                if contract_violations
                else ""
            )
            attempts += 1
            warnings.extend(
                str(item)
                for item in response.warnings
                if str(item)
            )
            response_metadata = (
                dict(response.metadata or {})
                if isinstance(response.metadata, dict)
                else {}
            )
            context_window_exceeded = bool(
                response_metadata.get("context_window_exceeded")
                or "context_window_exceeded" in set(response.warnings or [])
            )
            retry_metadata = {
                **dict(request.metadata),
                "semantic_retry_attempt": attempts,
                "semantic_retry_reason": retry.get("reason"),
                "semantic_retry_strategy": retry.get("strategy"),
            }
            if context_window_exceeded:
                retry_metadata["ctx_size"] = self._context_retry_size(
                    request=request,
                    response=response,
                )
                retry_metadata["semantic_retry_context_expanded"] = True
                retry_messages = list(request.messages)
                warnings.append("semantic_retry_context_expanded")
            else:
                retry_messages = [
                    *request.messages,
                    PromptMessage(
                        role="user",
                        content=(
                            "The previous candidate did not satisfy the "
                            "governed output contract. "
                            f"{hint}{violation_hint} "
                            "Return only the requested JSON object. "
                            "Do not add prose, markdown fences, tools, "
                            "permissions, evidence, or fields outside the "
                            "allowed contract."
                        ),
                    ),
                ]
            retry_request = request.model_copy(
                update={
                    "messages": retry_messages,
                    "metadata": retry_metadata,
                },
                deep=True,
            )
            response = self.invocation.invoke_role_model(
                retry_request
            )

    @staticmethod
    def _context_retry_size(*, request: ModelRequest, response: Any) -> int:
        metadata = (
            dict(getattr(response, "metadata", {}) or {})
            if isinstance(getattr(response, "metadata", None), dict)
            else {}
        )
        required_tokens = max(
            0,
            int(metadata.get("context_required_tokens") or 0),
        )
        current_ctx = max(
            0,
            int(
                metadata.get("ctx_size")
                or request.metadata.get("ctx_size")
                or 0
            ),
        )
        output_tokens = max(
            0,
            int(request.generation_config.max_tokens or 0),
        )
        margin_tokens = max(
            256,
            min(1024, output_tokens // 2 if output_tokens else 256),
        )
        observed_requirement = (
            required_tokens + output_tokens + margin_tokens
            if required_tokens
            else current_ctx + output_tokens + margin_tokens
        )
        return max(current_ctx + margin_tokens, observed_requirement, 2048)

    def _parse_json_object(
        self,
        content: Any,
        *,
        required_fields: list[str],
    ) -> dict[str, Any] | None:
        if not isinstance(content, str):
            return None
        text = content.strip()
        if not text:
            return None
        try:
            direct = json.loads(text)
        except (TypeError, ValueError):
            direct = None
        if isinstance(direct, dict) and all(field in direct for field in required_fields):
            return direct

        decoder = json.JSONDecoder()
        for index, char in enumerate(text):
            if char != "{":
                continue
            try:
                candidate, _end = decoder.raw_decode(text[index:])
            except ValueError:
                continue
            if not isinstance(candidate, dict):
                continue
            if all(field in candidate for field in required_fields):
                return candidate
        return None
