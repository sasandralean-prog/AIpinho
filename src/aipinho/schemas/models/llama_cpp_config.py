from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class LlamaCppRuntimeConfig(AIpinhoModel):
    default_ctx_size: int = 2048
    max_ctx_size: int = 4096
    default_n_predict: int = 256
    max_n_predict: int = 1024
    default_temperature: float = 0.2
    default_top_p: float = 0.9
    default_threads: int | None = None


class LlamaCppConfig(AIpinhoModel):
    provider_id: str = "llama_cpp.local"
    enabled: bool = False
    real_inference: bool = False
    executable_path: str | None = None
    working_directory: str | None = None
    allow_custom_args: bool = False
    allowed_args: list[str] = Field(default_factory=list)
    blocked_args: list[str] = Field(default_factory=list)
    use_shell: bool = False
    timeout_seconds: int = 60
    max_stdout_chars: int = 20000
    max_stderr_chars: int = 8000
    kill_on_timeout: bool = True
    runtime: LlamaCppRuntimeConfig = Field(default_factory=LlamaCppRuntimeConfig)
