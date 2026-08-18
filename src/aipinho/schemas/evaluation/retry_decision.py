from __future__ import annotations

from aipinho.schemas.common.base import AIpinhoModel


class RetryDecision(AIpinhoModel):
    should_retry: bool = False
    reason: str | None = None
    strategy: str | None = None
    max_retries: int = 1
    retry_prompt_hint: str | None = None
