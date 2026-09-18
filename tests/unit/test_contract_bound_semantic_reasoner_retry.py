from __future__ import annotations

import json
from types import SimpleNamespace

from aipinho.schemas.models.model_response import ModelResponse
from aipinho.services.semantics.contract_bound_semantic_reasoner import (
    ContractBoundSemanticReasoner,
)


class _Router:
    def select_model(self, **_kwargs):
        return SimpleNamespace(
            status="ok",
            model=SimpleNamespace(model_id="fixture-model"),
            provider=SimpleNamespace(provider_id="fixture-provider"),
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
):
    return ModelResponse(
        request_id="request_fixture",
        model_id="fixture-model",
        provider_id="fixture-provider",
        status=status,
        content=content,
        real_inference=True,
        warnings=list(warnings or []),
        evaluation_result={
            "status": evaluation_status,
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
