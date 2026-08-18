from __future__ import annotations

from aipinho.schemas.common.base import AIpinhoModel


class ModelDoctorRequest(AIpinhoModel):
    include_first_token_probe: bool = False
    operator_confirmed: bool = False
    include_manual_only: bool = True
    include_trace: bool = True
