from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.schemas.interaction.contracts import SpeakerTruthRequest
from aipinho.services.interaction.interaction_core import InteractionCockpitStatusService, SpeakerTruthService

router = APIRouter(prefix="/api/v1/interaction", tags=["interaction-cockpit"])


@router.get("/status")
def interaction_status() -> dict[str, object]:
    return InteractionCockpitStatusService().status()


@router.post("/speaker/validate")
def validate_speaker_message(request: SpeakerTruthRequest) -> dict[str, object]:
    result = SpeakerTruthService().from_event(request.source_event_id, request.requested_message)
    return {"status": "ok" if result.allowed else "blocked", "result": result.model_dump()}
