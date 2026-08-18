from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LucioClientResult:
    status: str
    text: str
    model: str
    error_code: str | None = None


class FakeLucioClient:
    def respond(
        self,
        *,
        prompt: str,
        model: str,
        timeout_seconds: int,
        max_output_chars: int,
        context_sanitized: str = "",
    ) -> LucioClientResult:
        del timeout_seconds, context_sanitized
        text = f"Lucio analisou o pedido em modo estrategico governado: {prompt.strip()}"
        return LucioClientResult(status="completed", text=text[:max_output_chars], model=model)


class OpenAILucioClient:
    def __init__(
        self,
        api_key: str | None,
        *,
        base_url: str | None = None,
        project: str | None = None,
        organization: str | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url or None
        self.project = project or None
        self.organization = organization or None

    def respond(
        self,
        *,
        prompt: str,
        model: str,
        timeout_seconds: int,
        max_output_chars: int,
        context_sanitized: str = "",
    ) -> LucioClientResult:
        if not self.api_key:
            return LucioClientResult(status="failed", text="", model=model, error_code="openai_api_key_missing")
        try:
            from openai import OpenAI
        except Exception:
            return LucioClientResult(status="failed", text="", model=model, error_code="openai_sdk_missing")

        instructions = (
            "Voce e Lucio, agente estrategico multimodal da AIpinho. "
            "Responda com conclusoes publicas e justificativas resumidas. "
            "Nao exponha chain-of-thought, segredos, tokens ou raw logs. "
            "Nao alegue execucao local sem evidencia de um child run governado."
        )
        input_text = prompt
        if context_sanitized:
            input_text = f"{context_sanitized}\n\nPedido atual:\n{prompt}"
        try:
            client = OpenAI(
                api_key=self.api_key,
                timeout=timeout_seconds,
                base_url=self.base_url,
                project=self.project,
                organization=self.organization,
            )
            response: Any = client.responses.create(
                model=model,
                instructions=instructions,
                input=input_text,
            )
            text = str(getattr(response, "output_text", "") or "")
            if not text:
                return LucioClientResult(status="failed", text="", model=model, error_code="openai_empty_response")
            return LucioClientResult(status="completed", text=text[:max_output_chars], model=model)
        except Exception as exc:
            return LucioClientResult(status="failed", text="", model=model, error_code=_safe_error_code(exc))


def _safe_error_code(exc: Exception) -> str:
    name = type(exc).__name__.lower()
    message = str(exc).lower()
    if "timeout" in name or "timeout" in message:
        return "openai_timeout"
    if "authentication" in name or "401" in message:
        return "openai_auth_error"
    if "rate" in name or "429" in message:
        return "openai_rate_limited"
    if "internalservererror" in name or "internal server error" in message or "500" in message:
        return "openai_internal_error"
    if "model" in message and any(
        marker in message
        for marker in ("not found", "does not exist", "unsupported", "not available")
    ):
        return "openai_model_unavailable"
    return "openai_provider_error"
