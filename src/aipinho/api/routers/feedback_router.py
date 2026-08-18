from __future__ import annotations

from fastapi import APIRouter

from aipinho.schemas.interaction.contracts import FeedbackRequest
from aipinho.services.interaction.interaction_core import FeedbackService

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])


@router.post("")
def create_feedback(request: FeedbackRequest) -> dict[str, object]:
    return {"status": "ok", "feedback": FeedbackService().create(request).model_dump()}


@router.get("")
def list_feedback(limit: int = 100) -> dict[str, object]:
    return {"status": "ok", "feedback": [item.model_dump() for item in FeedbackService().list(limit=limit)]}
