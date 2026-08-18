from fastapi import APIRouter, HTTPException
from aipinho.schemas.replay.contracts import ReplayCaptureRequest
from aipinho.services.replay.replay_core import ReplayCaptureService, ReplayCaseService, ReplayDiffService, ReplayHarnessService, ReplayRunnerService, ReplayStoreService, ReplayTraceService

router = APIRouter(prefix="/api/v1/replay", tags=["replay"])

@router.get("/status")
def status(): return ReplayHarnessService().status().model_dump()

@router.post("/capture")
def capture(request: ReplayCaptureRequest): return ReplayCaptureService().capture(request).model_dump()

@router.get("/snapshots")
def snapshots():
    items=ReplayStoreService().snapshots.list()
    return {"status":"ok","count":len(items),"snapshots":[i.model_dump() for i in items]}

@router.get("/snapshots/{snapshot_id}")
def snapshot(snapshot_id: str):
    item=ReplayStoreService().snapshots.get(snapshot_id)
    if item is None: raise HTTPException(status_code=404, detail="snapshot_not_found")
    return {"status":"ok","snapshot":item.model_dump()}

@router.get("/snapshots/{snapshot_id}/trace")
def snapshot_trace(snapshot_id: str):
    item=ReplayStoreService().snapshots.get(snapshot_id)
    if item is None: raise HTTPException(status_code=404, detail="snapshot_not_found")
    return {"status":"ok","trace":{"snapshot_id":snapshot_id,"sanitized":item.sanitization.sanitized}}

@router.post("/cases")
def create_case(payload: dict):
    try:
        case=ReplayCaseService().create(str(payload["snapshot_id"]), str(payload.get("title","Replay case")), str(payload.get("category","general")), list(payload.get("golden_expectations", [])))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="snapshot_not_found") from exc
    return {"status":"ok","case":case.model_dump()}

@router.get("/cases")
def cases():
    items=ReplayCaseService().list()
    return {"status":"ok","count":len(items),"cases":[i.model_dump() for i in items]}

@router.get("/cases/{case_id}")
def case(case_id: str):
    item=ReplayCaseService().get(case_id)
    if item is None: raise HTTPException(status_code=404, detail="case_not_found")
    return {"status":"ok","case":item.model_dump()}

@router.post("/cases/{case_id}/run")
def run_case(case_id: str):
    try: run=ReplayRunnerService().run(case_id)
    except FileNotFoundError as exc: raise HTTPException(status_code=404, detail="case_not_found") from exc
    return {"status":"ok","run":run.model_dump()}

@router.get("/runs/{run_id}")
def run(run_id: str):
    item=ReplayRunnerService().get(run_id)
    if item is None: raise HTTPException(status_code=404, detail="run_not_found")
    trace=ReplayTraceService().get(item.trace_id) if item.trace_id else None
    return {"status":"ok","run":item.model_dump(),"trace":trace.model_dump() if trace else None}

@router.get("/runs/{run_id}/diff")
def diff(run_id: str):
    item=ReplayDiffService().get_for_run(run_id)
    if item is None: raise HTTPException(status_code=404, detail="diff_not_found")
    return {"status":"ok","diff":item.model_dump()}
