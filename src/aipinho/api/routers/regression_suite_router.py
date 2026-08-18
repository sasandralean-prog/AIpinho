from fastapi import APIRouter, HTTPException
from aipinho.services.regression.regression_core import RegressionRunnerService, RegressionSuiteService

router = APIRouter(prefix="/api/v1/regression/suites", tags=["regression-suites"])

@router.get("")
def suites():
    items=RegressionSuiteService().list()
    return {"status":"ok","count":len(items),"suites":[i.model_dump() for i in items]}

@router.get("/{suite_id}")
def suite(suite_id: str):
    try: item=RegressionSuiteService().get(suite_id)
    except FileNotFoundError as exc: raise HTTPException(status_code=404, detail="suite_not_found") from exc
    return {"status":"ok","suite":item.model_dump()}

@router.post("/{suite_id}/run")
def run_suite(suite_id: str):
    try: result=RegressionRunnerService().run_suite(suite_id)
    except FileNotFoundError as exc: raise HTTPException(status_code=404, detail="suite_not_found") from exc
    return {"status":"ok","run":result.model_dump()}
