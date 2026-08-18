from __future__ import annotations

from aipinho.schemas.common.base import AIpinhoModel


class IntentEvidence(AIpinhoModel):
    kind: str
    value: str
    confidence: float = 0.0
    source: str = "prompt"