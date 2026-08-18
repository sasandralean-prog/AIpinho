from __future__ import annotations

from fastapi import APIRouter

from aipinho.schemas.evals.contracts import EvalRequest
from aipinho.services.evals.evaluation_workbench_service import EvaluationWorkbenchService
from aipinho.services.evals.eval_run_store import EvalRunStore

router = APIRouter(prefix="/api/v1/evals", tags=["evals"])


@router.get("/status")
def get_evals_status() -> dict[str, object]:
    return EvaluationWorkbenchService().status()


def _run(name: str, request: EvalRequest) -> dict[str, object]:
    result = EvaluationWorkbenchService().evaluate(name, request)
    body = result.model_dump()
    return {"status": result.status, "eval_run_id": result.eval_run_id, "read_only": result.read_only, "trace": body.get("trace"), "result": body}


@router.post("/model")
def eval_model(request: EvalRequest) -> dict[str, object]:
    return _run("model", request)


@router.post("/role")
def eval_role(request: EvalRequest) -> dict[str, object]:
    return _run("role", request)


@router.post("/rag")
def eval_rag(request: EvalRequest) -> dict[str, object]:
    return _run("rag", request)


@router.post("/citation-coverage")
def eval_citation_coverage(request: EvalRequest) -> dict[str, object]:
    return _run("citation_coverage", request)


@router.post("/context-grounding")
def eval_context_grounding(request: EvalRequest) -> dict[str, object]:
    return _run("context_grounding", request)


@router.post("/hallucination-signals")
def eval_hallucination_signals(request: EvalRequest) -> dict[str, object]:
    return _run("hallucination_signals", request)


@router.post("/latency-cost")
def eval_latency_cost(request: EvalRequest) -> dict[str, object]:
    return _run("latency_cost", request)


@router.post("/fallback-analysis")
def eval_fallback_analysis(request: EvalRequest) -> dict[str, object]:
    return _run("fallback_analysis", request)


@router.post("/vision-ocr")
def eval_vision_ocr(request: EvalRequest) -> dict[str, object]:
    return _run("vision_ocr", request)


@router.post("/end-to-end")
def eval_end_to_end(request: EvalRequest) -> dict[str, object]:
    return _run("end_to_end", request)


@router.get("/runs")
def list_eval_runs() -> dict[str, object]:
    runs = EvalRunStore().list()
    return {"status": "ok", "runs": runs, "count": len(runs)}


@router.get("/runs/{eval_run_id}")
def get_eval_run(eval_run_id: str) -> dict[str, object]:
    run = EvalRunStore().get(eval_run_id)
    return {"status": "ok" if run else "missing", "run": run}


@router.get("/runs/{eval_run_id}/trace")
def get_eval_trace(eval_run_id: str) -> dict[str, object]:
    run = EvalRunStore().get(eval_run_id)
    result = ((run or {}).get("result") or {}) if isinstance(run, dict) else {}
    return {"status": "ok" if result.get("trace") else "missing", "trace": result.get("trace")}


