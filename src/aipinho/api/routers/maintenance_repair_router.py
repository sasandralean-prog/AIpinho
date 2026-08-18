from fastapi import APIRouter, HTTPException
from aipinho.schemas.maintenance.contracts import RepairProposalRequest
from aipinho.services.maintenance.maintenance_core import (
    MaintenanceConfigChangePreviewService,
    MaintenancePatchPreviewService,
    MaintenanceRollbackPlanner,
    MaintenanceValidationRecommendationService,
    RepairHandoffService,
    RepairProposalService,
)

router = APIRouter(prefix="/api/v1/maintenance/repair", tags=["maintenance-repair"])

@router.post("/propose")
def propose(request: RepairProposalRequest) -> dict[str, object]:
    try:
        return {"status": "ok", "proposal": RepairProposalService().propose(request).model_dump()}
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

@router.get("/proposals")
def list_proposals() -> dict[str, object]:
    items = RepairProposalService().list()
    return {"status": "ok", "count": len(items), "proposals": [item.model_dump() for item in items]}

@router.get("/proposals/{proposal_id}")
def get_proposal(proposal_id: str) -> dict[str, object]:
    item = RepairProposalService().get(proposal_id)
    if item is None:
        raise HTTPException(status_code=404, detail="repair_proposal_not_found")
    return {"status": "ok", "proposal": item.model_dump()}

def _wrap(callable_):
    try:
        return callable_()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="repair_proposal_not_found") from exc

@router.post("/{proposal_id}/patch-preview")
def patch_preview(proposal_id: str) -> dict[str, object]:
    return {"status": "ok", "preview": _wrap(lambda: MaintenancePatchPreviewService().create(proposal_id)).model_dump()}

@router.post("/{proposal_id}/config-preview")
def config_preview(proposal_id: str) -> dict[str, object]:
    return {"status": "ok", "preview": _wrap(lambda: MaintenanceConfigChangePreviewService().create(proposal_id)).model_dump()}

@router.post("/{proposal_id}/validation-plan")
def validation_plan(proposal_id: str) -> dict[str, object]:
    return {"status": "ok", "validation": _wrap(lambda: MaintenanceValidationRecommendationService().create(proposal_id)).model_dump()}

@router.post("/{proposal_id}/rollback-plan")
def rollback_plan(proposal_id: str) -> dict[str, object]:
    return {"status": "ok", "rollback": _wrap(lambda: MaintenanceRollbackPlanner().create(proposal_id)).model_dump()}

@router.post("/{proposal_id}/handoff")
def handoff(proposal_id: str) -> dict[str, object]:
    return {"status": "ok", "handoff": _wrap(lambda: RepairHandoffService().create(proposal_id)).model_dump()}
