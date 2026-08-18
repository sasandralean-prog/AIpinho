from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class PromptBudget(AIpinhoModel):
    max_input_chars: int = 20000
    used_input_chars: int = 0
    estimated_tokens: int = 0
    truncated: bool = False
    omitted_items: list[str] = Field(default_factory=list)
    max_context_items: int = 20
    max_chars_per_context_item: int = 4000
    max_output_tokens: int = 512
