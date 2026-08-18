from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.schemas.self_healing import (
    SelfHealingApplyRequest,
    SelfHealingExportReportRequest,
    SelfHealingRejectRequest,
    SelfHealingScanRequest,
    SelfHealingTriageRequest,
)
from aipinho.services.agents.multi_agent_observability_service import MultiAgentObservabilityService
from aipinho.services.self_healing.self_healing_service import SelfHealingService

router = APIRouter(prefix="/api/v1/self-healing", tags=["governed-self-healing"])
dashboard_router = APIRouter(prefix="/api/v1/dashboard/state-consistency", tags=["governed-self-healing-dashboard"])


def _service() -> SelfHealingService:
    return SelfHealingService()


@router.get("/status")
def self_healing_status() -> dict[str, object]:
    return _service().status().model_dump()


@router.post("/scan")
def self_healing_scan(request: SelfHealingScanRequest) -> dict[str, object]:
    candidates = _service().scan(request)
    return {"status": "ok", "candidates": [candidate.model_dump() for candidate in candidates], "raw_default_visible": False}


@router.get("/candidates")
def list_self_healing_candidates(
    status: str | None = None,
    risk_level: str | None = None,
    detector_id: str | None = None,
) -> dict[str, object]:
    candidates = _service().candidates(status=status, risk_level=risk_level, detector_id=detector_id)
    return {"status": "ok", "candidates": [candidate.model_dump() for candidate in candidates], "raw_default_visible": False}


@router.get("/candidates/{candidate_id}")
def get_self_healing_candidate(candidate_id: str) -> dict[str, object]:
    candidate = _service().candidate(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="self_healing_candidate_not_found")
    return {"status": "ok", "candidate": candidate.model_dump(), "raw_default_visible": False}


@router.post("/candidates/{candidate_id}/triage")
def triage_self_healing_candidate(candidate_id: str, request: SelfHealingTriageRequest) -> dict[str, object]:
    try:
        candidate = _service().triage(candidate_id, request)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="self_healing_candidate_not_found") from exc
    return {"status": "ok", "candidate": candidate.model_dump(), "raw_default_visible": False}


@router.post("/candidates/{candidate_id}/apply")
def apply_self_healing_candidate(candidate_id: str, request: SelfHealingApplyRequest) -> dict[str, object]:
    try:
        run = _service().apply(candidate_id, request)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="self_healing_candidate_or_action_not_found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"status": run.status, "run": run.model_dump(), "raw_default_visible": False}


@router.post("/candidates/{candidate_id}/reject")
def reject_self_healing_candidate(candidate_id: str, request: SelfHealingRejectRequest) -> dict[str, object]:
    try:
        candidate = _service().reject(candidate_id, request)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="self_healing_candidate_not_found") from exc
    return {"status": "ok", "candidate": candidate.model_dump(), "raw_default_visible": False}


@router.get("/runs")
def list_self_healing_runs() -> dict[str, object]:
    return {"status": "ok", "runs": [run.model_dump() for run in _service().runs()], "raw_default_visible": False}


@router.get("/runs/{self_healing_run_id}")
def get_self_healing_run(self_healing_run_id: str) -> dict[str, object]:
    run = _service().run(self_healing_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="self_healing_run_not_found")
    return {"status": "ok", "run": run.model_dump(), "raw_default_visible": False}


@router.post("/export-report")
def export_self_healing_report(request: SelfHealingExportReportRequest) -> dict[str, object]:
    return _service().export_report(request)


@dashboard_router.post("/scan")
def scan_state_consistency() -> dict[str, object]:
    report = MultiAgentObservabilityService().state_consistency()
    candidates = _service().scan(SelfHealingScanRequest(detector_ids=["state_consistency"], persist=True))
    return {
        "status": "ok",
        "state_consistency": report.model_dump(),
        "self_healing_candidates": [candidate.model_dump() for candidate in candidates],
        "raw_default_visible": False,
    }
