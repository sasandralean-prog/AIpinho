from __future__ import annotations

from aipinho.schemas.common.base import AIpinhoModel


class ModelLatencyProfile(AIpinhoModel):
    model_id: str
    latency_class: str
    expected: str
    requires_warning: bool = False
