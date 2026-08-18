from fastapi import APIRouter, HTTPException
from aipinho.schemas.regression.contracts import RegressionPromotionRequest
from aipinho.services.regression.regression_core import RegressionCandidateService, RegressionCaseService, RegressionHarnessService, RegressionPromotionService, RegressionRunnerService

router = APIRouter(prefix="/api/v1/regression", tags=["regression"])

@router.get("/status")
def status(): return RegressionHarnessService().status().model_dump()

@router.post("/candidates")
def create_candidate(payload: dict):
    try:
        item=RegressionCandidateService().create(str(payload.get("source_type","manual")),str(payload.get("category","general")),str(payload.get("severity","medium")),list(payload.get("evidence",[])),dict(payload.get("expected_behavior",{})),payload.get("snapshot_id"))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"status":"ok","candidate":item.model_dump()}

@router.get("/candidates")
def candidates():
    items=RegressionCandidateService().list()
    return {"status":"ok","count":len(items),"candidates":[i.model_dump() for i in items]}

@router.post("/candidates/{candidate_id}/promote")
def promote(candidate_id: str, payload: dict):
    request=RegressionPromotionRequest(candidate_id=candidate_id,approved=bool(payload.get("approved",False)),validation_passed=bool(payload.get("validation_passed",False)),title=payload.get("title"))
    result=RegressionPromotionService().promote(request)
    if result.status=="blocked": raise HTTPException(status_code=409, detail=",".join(result.reasons))
    return result.model_dump()

@router.get("/cases")
def cases():
    items=RegressionCaseService().list()
    return {"status":"ok","count":len(items),"cases":[i.model_dump() for i in items]}

@router.get("/cases/{case_id}")
def case(case_id: str):
    item=RegressionCaseService().get(case_id)
    if item is None: raise HTTPException(status_code=404, detail="case_not_found")
    return {"status":"ok","case":item.model_dump()}

@router.post("/cases/{case_id}/run")
def run_case(case_id: str):
    try: result=RegressionRunnerService().run_stored_case(case_id)
    except FileNotFoundError as exc: raise HTTPException(status_code=404, detail="case_not_found") from exc
    return {"status":"ok","run":result.model_dump()}

@router.get("/runs/{run_id}")
def run(run_id: str):
    item=RegressionRunnerService().repository.get(run_id)
    if item is None: raise HTTPException(status_code=404, detail="run_not_found")
    return {"status":"ok","run":item.model_dump()}
