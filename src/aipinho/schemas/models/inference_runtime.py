from __future__ import annotations

from typing import Any

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class InferenceRuntimeFingerprint(AIpinhoModel):
    executable_path: str | None = None
    executable_sha256: str | None = None
    model_path: str | None = None
    model_sha256: str | None = None
    model_size_bytes: int | None = None
    model_mtime_ns: int | None = None
    cwd: str | None = None
    path_sha256: str | None = None
    env_sha256: str | None = None
    vulkan_sdk: str | None = None


class InferenceRuntimeTelemetry(AIpinhoModel):
    runtime: str = "inference_runtime"
    provider_type: str | None = None
    execution_mode: str | None = None
    model_id: str
    provider_id: str
    ctx_size: int | None = None
    max_output_tokens: int | None = None
    timeout_seconds: int | None = None
    prompt_chars: int = 0
    completion_chars: int = 0
    prompt_tokens_estimated: int = 0
    completion_tokens_estimated: int = 0
    parser: str | None = None
    json_valid: bool | None = None
    retry_count: int = 0
    timed_out: bool = False
    stdout_raw_chars: int = 0
    stdout_sanitized_chars: int = 0
    stderr_chars: int = 0
    fingerprint: InferenceRuntimeFingerprint = Field(default_factory=InferenceRuntimeFingerprint)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
