from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.models.model_doctor_check import ModelDoctorCheck


class ModelDoctorResult(AIpinhoModel):
    doctor_run_id: str
    model_id: str
    status: str
    checks: list[ModelDoctorCheck] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    trace_id: str | None = None
    created_at: str
