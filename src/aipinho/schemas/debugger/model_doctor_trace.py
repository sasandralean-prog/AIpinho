from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class ModelDoctorTrace(AIpinhoModel):
    trace_id: str
    doctor_run_id: str
    model_id: str | None = None
    status: str
    events: list[dict[str, object]] = Field(default_factory=list)
