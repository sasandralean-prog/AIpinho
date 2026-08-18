from __future__ import annotations

from aipinho.schemas.common.base import AIpinhoModel


class InferenceRuntimeLimits(AIpinhoModel):
    max_input_chars: int = 20000
    max_estimated_input_tokens: int = 4096
    max_output_tokens: int = 1024
    default_output_tokens: int = 256
    max_concurrent_invocations: int = 1
    timeout_seconds: int = 60
    max_stdout_chars: int = 20000
    max_stderr_chars: int = 8000
