from fastapi import APIRouter, HTTPException
from aipinho.schemas.maintenance.contracts import InvariantCheckRequest
from aipinho.services.maintenance.maintenance_core import InvariantChecker, InvariantRegistryService

router = APIRouter(prefix="/api/v1/maintenance/invariants", tags=["maintenance-invariants"])

@router.post("/check")
def check_invariants(request: InvariantCheckRequest) -> dict[str, object]:
    return InvariantChecker().check(request).model_dump()

@router.get("")
def list_invariants() -> dict[str, object]:
    items = InvariantRegistryService().list()
    return {"status": "ok", "count": len(items), "invariants": [item.model_dump() for item in items]}

@router.get("/{invariant_id}")
def get_invariant(invariant_id: str) -> dict[str, object]:
    item = InvariantRegistryService().get(invariant_id)
    if item is None:
        raise HTTPException(status_code=404, detail="invariant_not_found")
    return {"status": "ok", "invariant": item.model_dump()}
