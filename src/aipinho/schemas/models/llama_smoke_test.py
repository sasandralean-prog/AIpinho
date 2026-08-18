from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class LlamaSmokePrompt(AIpinhoModel):
    prompt_id: str
    text: str
    expected_contains_any: list[str] = Field(default_factory=list)
    max_prompt_chars: int = 500


class LlamaSmokePreview(AIpinhoModel):
    status: str = "blocked"
    process_started: bool = False
    gate_decision: dict[str, object] = Field(default_factory=dict)
    prompt_summary: dict[str, object] = Field(default_factory=dict)
    command_preview: dict[str, object] | None = None
    runtime_estimate: dict[str, object] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
