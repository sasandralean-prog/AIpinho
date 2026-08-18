from fastapi import APIRouter, HTTPException
from aipinho.repositories.regression.repositories import RegressionReportRepository, RegressionRunRepository

router = APIRouter(prefix="/api/v1/regression", tags=["regression-reports"])

@router.get("/runs/{run_id}/report")
def report(run_id: str):
    for item in RegressionReportRepository().list():
        if item.run_id == run_id:
            return {"status":"ok","report":item.model_dump()}
    raise HTTPException(status_code=404, detail="report_not_found")
