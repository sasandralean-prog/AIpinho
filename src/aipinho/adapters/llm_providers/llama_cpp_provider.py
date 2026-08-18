from __future__ import annotations

from aipinho.adapters.llm_providers.base_provider import BaseModelProvider
from aipinho.schemas.models.model_request import ModelRequest
from aipinho.schemas.models.model_response import ModelResponse
from aipinho.services.models.llama_cpp_provider import LlamaCppProvider as ControlledLlamaCppProvider


class LlamaCppProvider(BaseModelProvider):
    def __init__(self, inner: ControlledLlamaCppProvider | None = None) -> None:
        self.inner = inner or ControlledLlamaCppProvider()

    def status(self) -> dict[str, object]:
        return self.inner.status()

    def invoke(self, request: ModelRequest) -> ModelResponse:
        return self.inner.invoke(request)

    def invoke_preview(self, request: ModelRequest) -> dict[str, object]:
        return self.inner.invoke_preview(request)
