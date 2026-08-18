from __future__ import annotations

from aipinho.schemas.common.base import AIpinhoModel


class ModelRuntimeLimits(AIpinhoModel):
    timeout_seconds: int = 90
    max_output_tokens: int = 1024
    max_stdout_chars: int = 20000
    max_stderr_chars: int = 8000
