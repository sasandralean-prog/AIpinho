from fastapi import APIRouter
from aipinho.schemas.maintenance.contracts import DiagnosisRequest
from aipinho.services.maintenance.maintenance_core import MaintenancePlaneService

router = APIRouter(prefix="/api/v1/maintenance", tags=["maintenance-diagnosis"])

@router.post("/diagnose")
def diagnose(request: DiagnosisRequest) -> dict[str, object]:
    return MaintenancePlaneService().diagnose(request).model_dump()
