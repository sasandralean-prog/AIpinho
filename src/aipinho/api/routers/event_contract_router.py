from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.schemas.events.contracts import EventPublishRequest
from aipinho.services.events.event_core import EventContractRegistryService, EventContractValidator

router = APIRouter(prefix="/api/v1/events", tags=["event-contracts"])


@router.get("/status")
def event_status() -> dict[str, object]:
    return EventContractRegistryService().status()


@router.get("/contracts")
def event_contracts() -> dict[str, object]:
    return {"status": "ok", "contracts": {key: value.model_dump() for key, value in EventContractRegistryService().contracts().items()}}


@router.post("/validate")
def validate_event(request: EventPublishRequest) -> dict[str, object]:
    result = EventContractValidator().validate(request)
    return {"status": "ok" if result.allowed else "blocked", "validation": result.model_dump()}


@router.get("/contracts/{event_type}")
def event_contract(event_type: str) -> dict[str, object]:
    contract = EventContractRegistryService().get(event_type)
    if contract is None:
        raise HTTPException(status_code=404, detail="event_contract_not_found")
    return {"status": "ok", "contract": contract.model_dump()}

