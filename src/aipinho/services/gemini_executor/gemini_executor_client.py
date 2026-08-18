from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GeminiClientResult:
    status: str
    text: str
    model: str
    error_code: str | None = None
    fallback_used: bool = False


class FakeGeminiClient:
    def generate(self, *, prompt: str, model: str, timeout_seconds: int, max_output_chars: int) -> GeminiClientResult:
        text = "Resposta fake do Gemini Executor para teste governado."
        if prompt.strip():
            text = f"Gemini Executor recebeu o pedido e respondeu em modo governado: {prompt.strip()[:240]}"
        return GeminiClientResult(status="completed", text=text[:max_output_chars], model=model)


class GeminiApiClient:
    def __init__(self, primary_key: str | None, secondary_key: str | None = None, *, api_keys: tuple[str, ...] | list[str] | None = None) -> None:
        self.primary_key = primary_key
        self.secondary_key = secondary_key
        keys: list[str] = []
        for value in [*(api_keys or ()), primary_key, secondary_key]:
            key = (value or "").strip()
            if key and key not in keys:
                keys.append(key)
        self.api_keys = tuple(keys)

    def generate(self, *, prompt: str, model: str, timeout_seconds: int, max_output_chars: int) -> GeminiClientResult:
        if not self.api_keys:
            return GeminiClientResult(status="failed", text="", model=model, error_code="gemini_api_key_missing")
        try:
            from google import genai  # type: ignore
        except Exception:
            return GeminiClientResult(status="failed", text="", model=model, error_code="gemini_sdk_missing")
        last_error: Exception | None = None
        for index, api_key in enumerate(self.api_keys):
            try:
                client = genai.Client(api_key=api_key)
                result = client.models.generate_content(model=model, contents=prompt)
                text = str(getattr(result, "text", "") or "")
                return GeminiClientResult(status="completed", text=text[:max_output_chars], model=model, fallback_used=index > 0)
            except Exception as exc:
                last_error = exc
                if not _is_fallback_worthy(exc):
                    return GeminiClientResult(status="failed", text="", model=model, error_code=_safe_error_code(exc))
        return GeminiClientResult(status="failed", text="", model=model, error_code=_safe_error_code(last_error) if last_error else "gemini_provider_error")


def _is_fallback_worthy(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(marker in text for marker in ("quota", "rate", "auth", "permission", "unauthorized", "403", "429"))


def _safe_error_code(exc: Exception) -> str:
    text = type(exc).__name__.lower()
    if "timeout" in text:
        return "gemini_timeout"
    return "gemini_provider_error"
