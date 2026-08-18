from __future__ import annotations

from typing import Literal

from aipinho.schemas.common.base import AIpinhoModel

SegmentKind = Literal["main_request", "constraint", "path", "output_request", "condition", "question", "command", "unknown"]


class PromptSegment(AIpinhoModel):
    segment_id: str
    kind: SegmentKind
    text: str
    start: int = 0
    end: int = 0
    confidence: float = 0.0