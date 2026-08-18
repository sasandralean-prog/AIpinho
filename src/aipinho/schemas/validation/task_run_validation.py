from __future__ import annotations
from pydantic import Field
from aipinho.schemas.common.base import AIpinhoModel

class TaskRunValidation(AIpinhoModel):
    status: str
    run_id: str
    terminal_state_valid: bool = False
    events_valid: bool = False
    result_valid: bool = False
    findings: list[str] = Field(default_factory=list)
