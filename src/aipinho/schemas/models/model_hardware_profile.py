from __future__ import annotations

from aipinho.schemas.common.base import AIpinhoModel


class ModelHardwareProfile(AIpinhoModel):
    model_id: str
    hardware_class: str
    parameter_class: str | None = None
    cpu_only: bool = True
    fits_default_hardware: bool = True
    manual_only: bool = False
    warning: str | None = None
