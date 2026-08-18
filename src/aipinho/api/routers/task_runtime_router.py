from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Body, HTTPException, Query
from aipinho.schemas.runtime.task_cancellation import TaskCancellationRequest
from aipinho.schemas.runtime.task_run_request import TaskRunRequest
from aipinho.schemas.common.actor import Actor
from aipinho.schemas.common.base import AIpinhoModel
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.approvals.approval_task_continuation_service import ApprovalTaskContinuationService
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService
from aipinho.services.runtime.universal_task_session_service import UniversalTaskSessionService
from aipinho.services.speaker.task_speaker_update_service import TaskSpeakerUpdateService

router = APIRouter(prefix="/api/v1", tags=["task-runtime"])
service = TaskRuntimeService()
universal_sessions = UniversalTaskSessionService(store=service.store, approvals=service.approvals)


class TaskApprovalBatchRequest(AIpinhoModel):
    actor: Actor | None = None
    reason: str = ""


class CooperativeGraphRequest(AIpinhoModel):
    objective: str | None = None
    requested_nodes: list[str] = []


class ExecutionNodeUpdateRequest(AIpinhoModel):
    outputs: dict[str, Any] = {}
    artifact_refs: list[dict[str, Any]] = []
    memory_candidates: list[dict[str, Any]] = []
    speakertruth: dict[str, Any] = {}
    review: dict[str, Any] = {}
    validation: dict[str, Any] = {}
    reason: str = ""

def _not_found(value, detail):
    if value is None: raise HTTPException(status_code=404, detail=detail)
    return value

def _read_or_not_found(reader, detail):
    try:
        return _not_found(reader(), detail)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

def _universal_or_not_found(reader, detail):
    value = reader()
    if value is None:
        raise HTTPException(status_code=404, detail=detail)
    return value

@router.get("/task-runtime/status")
def runtime_status(): return service.status()

@router.get("/task-runtime/queue")
def runtime_queue(): return service.queue_status()

@router.post("/task-runs")
def create_run(request: TaskRunRequest): return service.create_run(request)

@router.post("/task-runs/from-draft/{draft_id}")
def create_from_draft(draft_id: str, options: dict[str, Any] | None = Body(default=None)):
    try: return service.create_from_draft(draft_id, options)
    except ValueError as exc:
        raise HTTPException(status_code=404 if "not_found" in str(exc) else 409, detail=str(exc)) from exc

@router.post("/task-runs/from-preview/{preview_id}")
def create_from_preview(preview_id: str, options: dict[str, Any] | None = Body(default=None)):
    try: return service.create_from_preview(preview_id, options)
    except ValueError as exc:
        raise HTTPException(status_code=404 if "not_found" in str(exc) else 409, detail=str(exc)) from exc

@router.post("/task-runs/{run_id}/start")
def start_run(run_id: str):
    try:
        run, result = service.start(run_id); return {"run": run, "result": result, "duplicate_safe": True}
    except ValueError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc

@router.post("/task-runs/{run_id}/cancel")
def cancel_run(run_id: str, request: TaskCancellationRequest | None = Body(default=None)):
    try: return service.cancel(run_id, request)
    except ValueError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc

@router.get("/task-runs/{run_id}")
def get_run(run_id: str): return _read_or_not_found(lambda: service.get_run(run_id), "task_run_not_found")

@router.get("/task-runs/{run_id}/events")
def get_events(run_id: str):
    _read_or_not_found(lambda: service.get_run(run_id), "task_run_not_found")
    return {"run_id": run_id, "events": service.get_events(run_id)}


@router.get("/task_runs/{run_id}/timeline")
@router.get("/task-runs/{run_id}/timeline")
def get_timeline(run_id: str):
    return _universal_or_not_found(
        lambda: service.get_timeline(run_id),
        "task_run_not_found",
    )


@router.get("/task_runs/{run_id}/truth")
@router.get("/task-runs/{run_id}/truth")
def get_runtime_truth(run_id: str):
    return _universal_or_not_found(
        lambda: service.get_runtime_truth(run_id),
        "task_run_not_found",
    )


@router.get("/task_runs/{run_id}")
@router.get("/task-runs/{run_id}/session")
def get_universal_task_session(run_id: str):
    return _universal_or_not_found(
        lambda: universal_sessions.get_session(run_id),
        "task_run_not_found",
    )


@router.get("/task_runs/{run_id}/events")
def get_universal_task_events(
    run_id: str,
    after_sequence: int | None = Query(default=None, ge=0),
    limit: int = Query(default=200, ge=1, le=1000),
):
    return _universal_or_not_found(
        lambda: universal_sessions.events(run_id, after_sequence=after_sequence, limit=limit),
        "task_run_not_found",
    )


@router.get("/task_runs/{run_id}/artifacts")
@router.get("/task-runs/{run_id}/artifacts")
def get_universal_task_artifacts(run_id: str):
    return _universal_or_not_found(
        lambda: universal_sessions.artifacts_for_run(run_id),
        "task_run_not_found",
    )


@router.get("/task_runs/{run_id}/summary")
@router.get("/task-runs/{run_id}/summary")
def get_universal_task_summary(run_id: str):
    return _universal_or_not_found(
        lambda: universal_sessions.summary(run_id),
        "task_run_not_found",
    )


@router.get("/task_runs")
def list_universal_task_sessions(
    status: str | None = None,
    session_id: str | None = None,
    contract_type: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
):
    return {
        "sessions": [
            session.model_dump()
            for session in universal_sessions.list_sessions(
                status=status,
                session_id=session_id,
                contract_type=contract_type,
                limit=limit,
            )
        ],
        "source": "universal_task_session",
    }


@router.get("/tasks/{task_id}/approvals")
def get_task_approvals(task_id: str, status: str | None = None, limit: int = Query(default=100, ge=1, le=500)):
    approvals = ApprovalService().list_for_task(task_id, status=status, limit=limit)
    return {"status": "ok", "task_id": task_id, "approvals": [approval.model_dump() for approval in approvals]}


@router.post("/tasks/{task_id}/approvals/approve-safe-batch")
def approve_task_safe_batch(task_id: str, request: TaskApprovalBatchRequest | None = Body(default=None)):
    try:
        return ApprovalTaskContinuationService().approve_safe_batch_for_task(
            task_id,
            actor=request.actor if request else None,
            reason=request.reason if request else "",
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/approvals/deny-safe-batch")
def deny_task_safe_batch(task_id: str, request: TaskApprovalBatchRequest | None = Body(default=None)):
    try:
        approvals = ApprovalService().safe_batch_for_task(task_id)
        if not approvals:
            return {
                "status": "blocked",
                "reason_code": "no_safe_pending_approvals",
                "task_id": task_id,
                "approvals": [],
                "resume_results": [],
            }
        decisions = ApprovalService().reject_batch(
            [approval.approval_id for approval in approvals],
            actor=request.actor if request else None,
            reason=request.reason if request else "safe_batch_denied",
            safe_only=True,
        )
        continuation = ApprovalTaskContinuationService()
        resume_results = [
            continuation.after_decision(approval, auto_process=False)
            for _decision, approval in decisions
        ]
        return {
            "status": "ok",
            "task_id": task_id,
            "approvals": [approval.model_dump() for _decision, approval in decisions],
            "decisions": [decision.model_dump() for decision, _approval in decisions],
            "resume_results": resume_results,
        }
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

@router.get("/task-runs/{run_id}/speaker/updates")
def get_speaker_updates(run_id: str, after_event_id: str | None = None, limit: int = Query(default=100, ge=1, le=500)):
    try:
        return TaskSpeakerUpdateService(runtime=service).updates(run_id, after_event_id=after_event_id, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@router.get("/task-runs/{run_id}/trace")
def get_trace(run_id: str):
    _read_or_not_found(lambda: service.get_run(run_id), "task_run_not_found")
    return {"run_id": run_id, "trace": service.get_trace(run_id)}

@router.get("/task-runs/{run_id}/execution-graph")
def get_execution_graph(run_id: str):
    _read_or_not_found(lambda: service.get_run(run_id), "task_run_not_found")
    graph = service.get_execution_graph(run_id)
    if graph is None:
        raise HTTPException(status_code=404, detail="execution_graph_not_found")
    return {"status": "ok", "run_id": run_id, "execution_graph": graph}


@router.get("/task-runs/{run_id}/planning/report")
def get_planning_report(run_id: str):
    _read_or_not_found(lambda: service.get_run(run_id), "task_run_not_found")
    report = service.get_planning_report(run_id)
    if report is None:
        raise HTTPException(status_code=404, detail="planning_report_not_found")
    return {"status": "ok", "run_id": run_id, "planning_report": report}


@router.post("/task-runs/{run_id}/planning/nodes/{node_id}/replan")
def replan_execution_graph_node(run_id: str, node_id: str, request: ExecutionNodeUpdateRequest | None = Body(default=None)):
    _read_or_not_found(lambda: service.get_run(run_id), "task_run_not_found")
    result = service.replan_execution_node(run_id, node_id, reason=(request.reason if request else "") or "node_replan_requested")
    if result is None:
        raise HTTPException(status_code=404, detail="planning_report_not_found")
    return {"status": "ok", "run_id": run_id, "node_id": node_id, **result}


@router.post("/task-runs/{run_id}/execution-graph/cooperative")
def create_cooperative_execution_graph(run_id: str, request: CooperativeGraphRequest | None = Body(default=None)):
    _read_or_not_found(lambda: service.get_run(run_id), "task_run_not_found")
    graph = service.create_cooperative_execution_graph(
        run_id,
        objective=request.objective if request else None,
        requested_nodes=request.requested_nodes if request else None,
    )
    return _universal_or_not_found(
        lambda: {"status": "ok", "run_id": run_id, "execution_graph": graph},
        "execution_graph_not_found",
    )


@router.get("/task-runs/{run_id}/execution-graph/poll")
def poll_execution_graph(run_id: str):
    _read_or_not_found(lambda: service.get_run(run_id), "task_run_not_found")
    graph = service.poll_execution_graph(run_id)
    return _universal_or_not_found(
        lambda: {"status": "ok", "run_id": run_id, "execution_graph": graph},
        "execution_graph_not_found",
    )


@router.post("/task-runs/{run_id}/execution-graph/nodes/{node_id}/start")
def start_execution_graph_node(run_id: str, node_id: str):
    _read_or_not_found(lambda: service.get_run(run_id), "task_run_not_found")
    graph = service.start_execution_node(run_id, node_id)
    return _universal_or_not_found(
        lambda: {"status": "ok", "run_id": run_id, "node_id": node_id, "execution_graph": graph},
        "execution_graph_not_found",
    )


@router.post("/task-runs/{run_id}/execution-graph/nodes/{node_id}/complete")
def complete_execution_graph_node(run_id: str, node_id: str, request: ExecutionNodeUpdateRequest | None = Body(default=None)):
    _read_or_not_found(lambda: service.get_run(run_id), "task_run_not_found")
    payload = request or ExecutionNodeUpdateRequest()
    graph = service.complete_execution_node(
        run_id,
        node_id,
        outputs=payload.outputs,
        artifact_refs=payload.artifact_refs,
        memory_candidates=payload.memory_candidates,
        speakertruth=payload.speakertruth,
        review=payload.review,
        validation=payload.validation,
    )
    return _universal_or_not_found(
        lambda: {"status": "ok", "run_id": run_id, "node_id": node_id, "execution_graph": graph},
        "execution_graph_not_found",
    )


@router.post("/task-runs/{run_id}/execution-graph/nodes/{node_id}/fail")
def fail_execution_graph_node(run_id: str, node_id: str, request: ExecutionNodeUpdateRequest | None = Body(default=None)):
    _read_or_not_found(lambda: service.get_run(run_id), "task_run_not_found")
    graph = service.fail_execution_node(run_id, node_id, reason=(request.reason if request else "") or "node_failed")
    return _universal_or_not_found(
        lambda: {"status": "ok", "run_id": run_id, "node_id": node_id, "execution_graph": graph},
        "execution_graph_not_found",
    )


@router.post("/task-runs/{run_id}/execution-graph/nodes/{node_id}/retry")
def retry_execution_graph_node(run_id: str, node_id: str, request: ExecutionNodeUpdateRequest | None = Body(default=None)):
    _read_or_not_found(lambda: service.get_run(run_id), "task_run_not_found")
    graph = service.retry_execution_node(run_id, node_id, reason=(request.reason if request else "") or "retry_node_requested")
    return _universal_or_not_found(
        lambda: {"status": "ok", "run_id": run_id, "node_id": node_id, "execution_graph": graph},
        "execution_graph_not_found",
    )


@router.post("/task-runs/{run_id}/execution-graph/nodes/{node_id}/cancel")
def cancel_execution_graph_node(run_id: str, node_id: str, request: ExecutionNodeUpdateRequest | None = Body(default=None)):
    _read_or_not_found(lambda: service.get_run(run_id), "task_run_not_found")
    graph = service.cancel_execution_node(run_id, node_id, reason=(request.reason if request else "") or "node_cancelled")
    return _universal_or_not_found(
        lambda: {"status": "ok", "run_id": run_id, "node_id": node_id, "execution_graph": graph},
        "execution_graph_not_found",
    )

@router.get("/task-runs/{run_id}/result")
def get_result(run_id: str): return _read_or_not_found(lambda: service.get_result(run_id), "task_run_result_not_found")

@router.get("/task-runs")
def list_runs(status: str | None = None, session_id: str | None = None, contract_type: str | None = None, created_after: str | None = None, limit: int = Query(default=100, ge=1, le=1000)):
    return {"runs": service.list_runs(status=status, session_id=session_id, contract_type=contract_type, created_after=created_after, limit=limit)}
