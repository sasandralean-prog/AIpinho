from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.services.evals.eval_run_store import EvalRunStore

router = APIRouter(prefix="/api/v1/evals/reports", tags=["eval-reports"])


@router.get("/{report_id}")
def get_eval_report(report_id: str) -> dict[str, object]:
    if report_id == "latest":
        runs = EvalRunStore().list()
        return {"status": "ok", "report": {"report_id": "latest", "runs": runs[:20]}}
    raise HTTPException(status_code=404, detail="eval_report_not_found")
