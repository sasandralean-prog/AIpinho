from __future__ import annotations

import json
from typing import Any

from aipinho.schemas.models.model_request import ModelRequest
from aipinho.schemas.prompts.prompt_message import PromptMessage
from aipinho.services.models.model_invocation_service import ModelInvocationService
from aipinho.services.models.model_router_service import ModelRouterService


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
        timeout_seconds: int = 45,
    ) -> None:
        self.router = router or ModelRouterService()
        self.invocation = invocation or ModelInvocationService(router=self.router)
        self.timeout_seconds = max(1, int(timeout_seconds))

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
            },
            safety_envelope={
                "envelope_id": "semantic_reasoning_readonly",
                "rules": ["no_tools", "no_files", "no_patch", "no_side_effects", "candidate_only"],
            },
            metadata={
                "purpose": "chat",
                "role_id": role_id,
                "role_pipeline_controlled_inference": True,
                "semantic_goal": semantic_goal,
                "max_stdout_chars": 12000,
                "timeout_seconds": self.timeout_seconds,
            },
        )
        request.generation_config.max_tokens = max_tokens
        response, retry_attempts, retry_warnings = (
            self._invoke_with_governed_retry(request)
        )
        warnings = list(
            dict.fromkeys(
                [*retry_warnings, *response.warnings]
            )
        )
        if response.status not in {"completed", "degraded"}:
            return {
                "status": "unavailable",
                "reason_code": "SEMANTIC_REASONER_INVOCATION_UNAVAILABLE",
                "model_id": response.model_id,
                "response_id": response.response_id,
                "warnings": warnings,
                "retry_attempts": retry_attempts,
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
                "retry_attempts": retry_attempts,
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
            "retry_attempts": retry_attempts,
        }

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
            attempts += 1
            warnings.extend(
                str(item)
                for item in response.warnings
                if str(item)
            )
            retry_request = request.model_copy(
                update={
                    "messages": [
                        *request.messages,
                        PromptMessage(
                            role="user",
                            content=(
                                "The previous candidate did not satisfy the "
                                "governed output contract. "
                                f"{hint} "
                                "Return only the requested JSON object. "
                                "Do not add prose, markdown fences, tools, "
                                "permissions, evidence, or fields outside the "
                                "allowed contract."
                            ),
                        ),
                    ],
                    "metadata": {
                        **dict(request.metadata),
                        "semantic_retry_attempt": attempts,
                        "semantic_retry_reason": retry.get("reason"),
                        "semantic_retry_strategy": retry.get("strategy"),
                    },
                },
                deep=True,
            )
            response = self.invocation.invoke_role_model(
                retry_request
            )

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
