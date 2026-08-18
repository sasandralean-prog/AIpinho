from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from aipinho.schemas.external_collaboration import (
    ContinuousCollaborationStartRequest,
    ExternalAdapterEvaluationRequest,
    ExternalAdapterReviewRequest,
    ExternalConversationCreateRequest,
    ExternalReviewCreateRequest,
    ExternalTaskCreateRequest,
    SuccessEvaluationCreateRequest,
    SuccessContractCreateRequest,
)
from aipinho.schemas.runtime.delegation_contract import DelegationCreateRequest
from aipinho.services.external_collaboration_service import ExternalCollaborationService

router = APIRouter(prefix="/api/v1/external", tags=["external-collaboration"])


def _service() -> ExternalCollaborationService:
    return ExternalCollaborationService()


def _not_found(value, detail: str):
    if value is None:
        raise HTTPException(status_code=404, detail=detail)
    return value


@router.get("/adapters")
def list_adapters() -> dict[str, object]:
    return {"status": "ok", "adapters": _service().list_adapters()}


@router.post("/delegation-decisions")
def decide_delegation(request: DelegationCreateRequest) -> dict[str, object]:
    decision = _service().decide_delegation(request)
    return {"status": "ok", "decision": decision.model_dump(), "authority": "aipinho"}


@router.post("/delegations")
def create_delegation(request: DelegationCreateRequest) -> dict[str, object]:
    try:
        return _service().create_delegation(request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/delegations")
def list_delegations(
    parent_run_id: str | None = None,
    child_run_id: str | None = None,
    status: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
) -> dict[str, object]:
    rows = _service().list_delegations(parent_run_id=parent_run_id, child_run_id=child_run_id, status=status, limit=limit)
    return {"status": "ok", "delegations": [row.model_dump() for row in rows], "authority": "aipinho"}


@router.get("/delegations/{delegation_id}")
def get_delegation(delegation_id: str) -> dict[str, object]:
    row = _not_found(_service().get_delegation(delegation_id), "delegation_not_found")
    return {"status": "ok", "delegation": row.model_dump(), "authority": "aipinho"}


@router.post("/delegations/{delegation_id}/poll")
def poll_delegation(delegation_id: str) -> dict[str, object]:
    return _not_found(_service().poll_delegation(delegation_id), "delegation_not_found")


@router.post("/adapters/{adapter_id}/review")
def adapt_review(adapter_id: str, request: ExternalAdapterReviewRequest) -> dict[str, object]:
    try:
        return _service().adapt_and_receive_review(adapter_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/collaboration-sessions/{session_id}/adapters/{adapter_id}/success-evaluation")
@router.post("/adapters/{adapter_id}/success-evaluation")
def adapt_success_evaluation(adapter_id: str, session_id: str, request: ExternalAdapterEvaluationRequest) -> dict[str, object]:
    try:
        return _service().adapt_and_receive_success_evaluation(adapter_id, session_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/success-contracts")
def create_success_contract(request: SuccessContractCreateRequest) -> dict[str, object]:
    contract = _service().create_success_contract(request)
    return {"status": "ok", "success_contract": contract.model_dump(), "authority": "aipinho"}


@router.get("/success-contracts/{contract_id}")
def get_success_contract(contract_id: str) -> dict[str, object]:
    contract = _not_found(_service().get_success_contract(contract_id), "success_contract_not_found")
    return {"status": "ok", "success_contract": contract.model_dump(), "authority": "aipinho"}


@router.post("/conversations")
def create_conversation(request: ExternalConversationCreateRequest) -> dict[str, object]:
    conversation = _service().create_conversation(request)
    return {"status": "ok", "conversation": conversation.model_dump()}


@router.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str) -> dict[str, object]:
    conversation = _not_found(_service().get_conversation(conversation_id), "external_conversation_not_found")
    return {"status": "ok", "conversation": conversation.model_dump()}


@router.post("/collaboration-sessions")
def start_collaboration_session(request: ContinuousCollaborationStartRequest) -> dict[str, object]:
    try:
        session = _service().start_continuous_session(request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "ok", "session": session.model_dump(), "authority": "aipinho"}


@router.get("/collaboration-sessions")
def list_collaboration_sessions(
    task_run_id: str | None = None,
    status: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
) -> dict[str, object]:
    sessions = _service().list_continuous_sessions(task_run_id=task_run_id, status=status, limit=limit)
    return {"status": "ok", "sessions": [session.model_dump() for session in sessions]}


@router.get("/collaboration-sessions/{session_id}")
def get_collaboration_session(session_id: str) -> dict[str, object]:
    session = _not_found(_service().get_continuous_session(session_id), "continuous_session_not_found")
    return {"status": "ok", "session": session.model_dump(), "authority": "aipinho"}


@router.post("/collaboration-sessions/{session_id}/poll")
def poll_collaboration_session(session_id: str) -> dict[str, object]:
    payload = _not_found(_service().poll_continuous_session(session_id), "continuous_session_not_found")
    return {"status": "ok", **payload.model_dump()}


@router.post("/collaboration-sessions/{session_id}/evaluations")
def receive_success_evaluation(session_id: str, request: SuccessEvaluationCreateRequest) -> dict[str, object]:
    payload = _not_found(_service().receive_success_evaluation(session_id, request), "continuous_session_not_found")
    return payload


@router.get("/collaboration-sessions/{session_id}/evaluations")
def list_success_evaluations(session_id: str, limit: int = Query(default=100, ge=1, le=1000)) -> dict[str, object]:
    evaluations = _service().list_success_evaluations(session_id=session_id, limit=limit)
    return {"status": "ok", "evaluations": [evaluation.model_dump() for evaluation in evaluations], "authority": "aipinho"}


@router.post("/tasks")
def submit_external_task(request: ExternalTaskCreateRequest) -> dict[str, object]:
    try:
        return _service().submit_task(request)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/tasks/{external_task_id}")
def get_external_task(external_task_id: str) -> dict[str, object]:
    return _not_found(_service().task_payload(external_task_id), "external_task_not_found")


@router.get("/tasks/{external_task_id}/progress")
def external_task_progress(external_task_id: str) -> dict[str, object]:
    return _not_found(_service().task_progress(external_task_id), "external_task_not_found")


@router.get("/tasks/{external_task_id}/summary")
def external_task_summary(external_task_id: str) -> dict[str, object]:
    return _not_found(_service().task_summary(external_task_id), "external_task_not_found")


@router.get("/tasks/{external_task_id}/artifacts")
def external_task_artifacts(external_task_id: str) -> dict[str, object]:
    return _not_found(_service().task_artifacts(external_task_id), "external_task_not_found")


@router.post("/reviews")
def receive_external_review(request: ExternalReviewCreateRequest) -> dict[str, object]:
    review = _service().receive_review(request)
    return {
        "status": "ok",
        "review": review.model_dump(),
        "authority": "aipinho",
        "external_may_execute": False,
    }


@router.get("/reviews")
def list_external_reviews(
    task_run_id: str | None = None,
    external_task_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
) -> dict[str, object]:
    reviews = _service().list_reviews(task_run_id=task_run_id, external_task_id=external_task_id, limit=limit)
    return {"status": "ok", "reviews": [review.model_dump() for review in reviews], "authority": "aipinho"}


@router.get("/reviews/{review_id}")
def get_external_review(review_id: str) -> dict[str, object]:
    review = _not_found(_service().get_review(review_id), "external_review_not_found")
    return {"status": "ok", "review": review.model_dump(), "authority": "aipinho"}
