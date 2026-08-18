from __future__ import annotations
from aipinho.schemas.common.actor import Actor
from aipinho.schemas.common.base import AIpinhoModel

class TaskCancellationRequest(AIpinhoModel):
    reason: str = "user_requested"
    requested_by: Actor = Actor(type="user", id="local_operator")

class TaskCancellationResult(AIpinhoModel):
    run_id: str
    status: str
    cancellation_requested: bool
    message: str
