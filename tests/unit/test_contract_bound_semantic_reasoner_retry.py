from __future__ import annotations

import json
from types import SimpleNamespace

from aipinho.schemas.models.model_response import ModelResponse
from aipinho.services.semantics.contract_bound_semantic_reasoner import (
    ContractBoundSemanticReasoner,
)


class _Router:
    def select_model(self, **kwargs):
        model_id = str(
            kwargs.get("requested_model_id")
            or "fixture-model"
        )
        return SimpleNamespace(
            status="ok",
            model=SimpleNamespace(
                model_id=model_id,
                hardware_class="medium_cpu",
            ),
            provider=SimpleNamespace(provider_id="fixture-provider"),
            warnings=[],
        )


class _NoFallback:
    def decide(
        self,
        _binding,
        *,
        reason,
        attempt=0,
        enforce_runtime_policy=False,
    ):
        return SimpleNamespace(
            fallback_allowed=False,
            fallback_model_id=None,
            blocked_reasons=["fixture_fallback_denied"],
            reason=reason,
        )


class _Invocation:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def invoke_role_model(self, request):
        self.requests.append(request)
        return self.responses[len(self.requests) - 1]


def _response(
    *,
    status,
    content,
    evaluation_status,
    retry,
    warnings=None,
    model_id="fixture-model",
    metadata=None,
    violations=None,
):
    return ModelResponse(
        request_id="request_fixture",
        model_id=model_id,
        provider_id="fixture-provider",
        status=status,
        content=content,
        real_inference=True,
        warnings=list(warnings or []),
        metadata=dict(metadata or {}),
        evaluation_result={
            "status": evaluation_status,
            "violations": list(violations or []),
            "retry_decision": retry,
        },
    )


def test_reasoner_executes_bounded_governed_retry_for_invalid_json() -> None:
    first = _response(
        status="degraded",
        content="not-json",
        evaluation_status="needs_retry",
        retry={
            "should_retry": True,
            "reason": "invalid_json",
            "strategy": "ask_for_json_only",
            "max_retries": 1,
            "retry_prompt_hint": (
                "Return only valid JSON matching the requested fields."
            ),
        },
        warnings=["invalid_json"],
    )
    second = _response(
        status="completed",
        content=json.dumps(
            {
                "answer": "ok",
                "confidence": 0.9,
            }
        ),
        evaluation_status="accepted",
        retry={
            "should_retry": False,
            "reason": "not_retryable",
            "max_retries": 1,
        },
    )
    invocation = _Invocation([first, second])
    reasoner = ContractBoundSemanticReasoner(
        router=_Router(),  # type: ignore[arg-type]
        invocation=invocation,  # type: ignore[arg-type]
    )

    proposal = reasoner.propose_json(
        semantic_goal="classify fixture",
        payload={"structured": True},
        allowed_fields=["answer", "confidence"],
        required_fields=["answer", "confidence"],
    )

    assert proposal["status"] == "candidate"
    assert proposal["retry_attempts"] == 1
    assert len(invocation.requests) == 2
    retry_request = invocation.requests[1]
    assert retry_request.metadata["semantic_retry_attempt"] == 1
    assert retry_request.metadata["semantic_retry_reason"] == "invalid_json"
    assert (
        "Return only valid JSON matching the requested fields."
        in retry_request.messages[-1].content
    )
    assert "invalid_json" in proposal["warnings"]




def test_reasoner_retries_nested_contract_violation_with_exact_path() -> None:
    first = _response(
        status="degraded",
        content=json.dumps(
            {
                "assessments": [
                    {
                        "limitation_id": "lim_1",
                        "impact": "COMPATIBLE",
                        "constraints": [],
                    }
                ],
                "confidence": 0.9,
                "rationale": "global rationale",
            }
        ),
        evaluation_status="needs_retry",
        violations=[
            "missing_required_field:assessments[0].rationale"
        ],
        retry={
            "should_retry": True,
            "reason": "missing_required_field",
            "strategy": "ask_for_missing_fields",
            "max_retries": 1,
            "retry_prompt_hint": (
                "Include every required field from the output contract, "
                "including nested fields."
            ),
        },
    )
    second = _response(
        status="completed",
        content=json.dumps(
            {
                "assessments": [
                    {
                        "limitation_id": "lim_1",
                        "impact": "COMPATIBLE",
                        "constraints": [],
                        "rationale": "bounded rationale",
                    }
                ],
                "confidence": 0.9,
                "rationale": "global rationale",
            }
        ),
        evaluation_status="accepted",
        retry={
            "should_retry": False,
            "reason": "not_retryable",
            "max_retries": 1,
        },
    )
    invocation = _Invocation([first, second])
    reasoner = ContractBoundSemanticReasoner(
        router=_Router(),  # type: ignore[arg-type]
        invocation=invocation,  # type: ignore[arg-type]
    )

    proposal = reasoner.propose_json(
        semantic_goal="assess bounded fixture",
        payload={
            "output_schema": {
                "assessments": {
                    "type": "list",
                    "item": {
                        "limitation_id": {
                            "type": "string",
                            "enum": ["lim_1"],
                        },
                        "impact": {
                            "type": "string",
                            "enum": ["COMPATIBLE"],
                        },
                        "constraints": "list[string]",
                        "rationale": "non_empty_string",
                    },
                    "required_count": 1,
                },
                "confidence": "number_between_0_and_1",
                "rationale": "non_empty_string",
            }
        },
        allowed_fields=["assessments", "confidence", "rationale"],
        required_fields=["assessments", "confidence", "rationale"],
    )

    assert proposal["status"] == "candidate"
    assert proposal["retry_attempts"] == 1
    retry_request = invocation.requests[1]
    assert (
        "missing_required_field:assessments[0].rationale"
        in retry_request.messages[-1].content
    )
    assert retry_request.output_contract["json_shape"]["assessments"][
        "required_count"
    ] == 1
    assert (
        proposal["candidate"]["assessments"][0]["rationale"]
        == "bounded rationale"
    )


def test_reasoner_context_overflow_retry_expands_context_without_prompt_growth() -> None:
    first = _response(
        status="degraded",
        content=(
            "Error: request (3131 tokens) exceeds the available context size "
            "(3072 tokens), try increasing it"
        ),
        evaluation_status="needs_retry",
        retry={
            "should_retry": True,
            "reason": "truncation",
            "strategy": "reduce_output_scope",
            "max_retries": 1,
            "retry_prompt_hint": (
                "Reduce scope and complete the response without truncation."
            ),
        },
        warnings=["llama_cli_error", "context_window_exceeded"],
        metadata={
            "context_window_exceeded": True,
            "context_required_tokens": 3131,
            "context_available_tokens": 3072,
            "ctx_size": 3038,
        },
    )
    second = _response(
        status="completed",
        content=json.dumps({"answer": "ok"}),
        evaluation_status="accepted",
        retry={
            "should_retry": False,
            "reason": "not_retryable",
            "max_retries": 1,
        },
    )
    invocation = _Invocation([first, second])
    reasoner = ContractBoundSemanticReasoner(
        router=_Router(),  # type: ignore[arg-type]
        invocation=invocation,  # type: ignore[arg-type]
    )

    proposal = reasoner.propose_json(
        semantic_goal="classify fixture",
        payload={"structured": True},
        allowed_fields=["answer"],
        required_fields=["answer"],
    )

    assert proposal["status"] == "candidate"
    assert proposal["retry_attempts"] == 1
    assert "semantic_retry_context_expanded" in proposal["warnings"]
    assert len(invocation.requests) == 2
    first_request, retry_request = invocation.requests
    assert [item.content for item in retry_request.messages] == [
        item.content for item in first_request.messages
    ]
    assert retry_request.metadata["semantic_retry_context_expanded"] is True
    assert retry_request.metadata["ctx_size"] >= 3899


def test_reasoner_does_not_retry_nonretryable_response() -> None:
    response = _response(
        status="blocked",
        content="blocked",
        evaluation_status="rejected",
        retry={
            "should_retry": False,
            "reason": "critical_safety_violation",
            "max_retries": 1,
        },
        warnings=["critical_safety_violation"],
    )
    invocation = _Invocation([response])
    reasoner = ContractBoundSemanticReasoner(
        router=_Router(),  # type: ignore[arg-type]
        invocation=invocation,  # type: ignore[arg-type]
        fallback=_NoFallback(),  # type: ignore[arg-type]
    )

    proposal = reasoner.propose_json(
        semantic_goal="classify fixture",
        payload={"structured": True},
        allowed_fields=["answer"],
        required_fields=["answer"],
    )

    assert proposal["status"] == "unavailable"
    assert proposal["retry_attempts"] == 0
    assert len(invocation.requests) == 1



def test_reasoner_fails_closed_when_role_prompt_budget_is_exceeded() -> None:
    invocation = _Invocation([])
    reasoner = ContractBoundSemanticReasoner(
        router=_Router(),  # type: ignore[arg-type]
        invocation=invocation,  # type: ignore[arg-type]
    )

    proposal = reasoner.propose_json(
        semantic_goal="bounded fixture",
        payload={"oversized": "x" * 7000},
        allowed_fields=["answer"],
        required_fields=["answer"],
        role_id="semantic_interpreter",
    )

    assert proposal["status"] == "unavailable"
    assert (
        proposal["reason_code"]
        == "SEMANTIC_REASONER_ROLE_BUDGET_EXCEEDED"
    )
    assert "prompt_budget_exceeded" in proposal["warnings"]
    assert proposal["role_budget"]["exceeded"] is True
    assert invocation.requests == []


def test_reasoner_uses_role_budget_for_timeout_and_output_cap() -> None:
    response = _response(
        status="completed",
        content=json.dumps({"answer": "ok"}),
        evaluation_status="accepted",
        retry={
            "should_retry": False,
            "reason": "not_retryable",
            "max_retries": 0,
        },
    )
    invocation = _Invocation([response])
    reasoner = ContractBoundSemanticReasoner(
        router=_Router(),  # type: ignore[arg-type]
        invocation=invocation,  # type: ignore[arg-type]
    )

    proposal = reasoner.propose_json(
        semantic_goal="plan next governed unit",
        payload={"structured": True},
        allowed_fields=["answer"],
        required_fields=["answer"],
        role_id="planner",
        max_tokens=1600,
    )

    assert proposal["status"] == "candidate"
    assert len(invocation.requests) == 1
    request = invocation.requests[0]
    assert request.metadata["timeout_seconds"] == 90
    assert request.generation_config.max_tokens == 1024
    assert request.metadata["role_budget"]["budget_class"] == "medium"


def test_reasoner_uses_declared_model_fallback_with_same_contract() -> None:
    primary = _response(
        status="degraded",
        content="not-json",
        evaluation_status="needs_retry",
        retry={
            "should_retry": False,
            "reason": "timeout",
            "max_retries": 0,
        },
        warnings=["timeout", "invalid_json"],
    )
    fallback = _response(
        status="completed",
        content=json.dumps(
            {
                "answer": "fallback-ok",
                "confidence": 0.88,
            }
        ),
        evaluation_status="accepted",
        retry={
            "should_retry": False,
            "reason": "not_retryable",
            "max_retries": 0,
        },
        model_id="qwen3_4b_thinking_distill_q4_k_m",
    )
    invocation = _Invocation([primary, fallback])
    reasoner = ContractBoundSemanticReasoner(
        router=_Router(),  # type: ignore[arg-type]
        invocation=invocation,  # type: ignore[arg-type]
    )

    proposal = reasoner.propose_json(
        semantic_goal="plan next governed unit",
        payload={"structured": True},
        allowed_fields=["answer", "confidence"],
        required_fields=["answer", "confidence"],
        role_id="planner",
    )

    assert proposal["status"] == "candidate"
    assert proposal["candidate"]["answer"] == "fallback-ok"
    assert proposal["fallback_used"] is True
    assert (
        proposal["fallback_model_id"]
        == "qwen3_4b_thinking_distill_q4_k_m"
    )
    assert "semantic_model_fallback_used" in proposal["warnings"]
    assert len(invocation.requests) == 2
    first, second = invocation.requests
    assert first.model_id == "fixture-model"
    assert second.model_id == "qwen3_4b_thinking_distill_q4_k_m"
    assert second.output_contract == first.output_contract
    assert second.safety_envelope == first.safety_envelope
    assert second.metadata["semantic_model_fallback"] is True
    assert (
        second.metadata["semantic_primary_model_id"]
        == "fixture-model"
    )
    assert (
        second.metadata["semantic_fallback_reason"]
        == "needs_retry"
    )


def test_reasoner_fallback_remains_fail_closed_when_policy_denies() -> None:
    response = _response(
        status="completed",
        content="not-json",
        evaluation_status="accepted",
        retry={
            "should_retry": False,
            "reason": "not_retryable",
            "max_retries": 0,
        },
    )
    invocation = _Invocation([response])
    reasoner = ContractBoundSemanticReasoner(
        router=_Router(),  # type: ignore[arg-type]
        invocation=invocation,  # type: ignore[arg-type]
        fallback=_NoFallback(),  # type: ignore[arg-type]
    )

    proposal = reasoner.propose_json(
        semantic_goal="classify fixture",
        payload={"structured": True},
        allowed_fields=["answer"],
        required_fields=["answer"],
    )

    assert proposal["status"] == "invalid"
    assert proposal["reason_code"] == "SEMANTIC_REASONER_INVALID_JSON"
    assert proposal["fallback_used"] is False
    assert "fixture_fallback_denied" in proposal["warnings"]
    assert len(invocation.requests) == 1
