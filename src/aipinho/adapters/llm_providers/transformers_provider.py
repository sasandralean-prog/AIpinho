from __future__ import annotations

from aipinho.adapters.llm_providers.base_provider import BaseModelProvider
from aipinho.schemas.models.model_request import ModelRequest
from aipinho.schemas.models.model_response import ModelResponse, ModelUsage


class TransformersProvider(BaseModelProvider):
    def status(self) -> dict[str, object]:
        return {"status": "disabled", "provider": "transformers.local", "real_inference": False}

    def invoke(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(request_id=request.request_id, model_id=request.model_id, provider_id=request.provider_id, status="blocked", content="Transformers provider disabled in Sprint 10.", usage=ModelUsage(), finish_reason="blocked", real_inference=False, warnings=["provider_disabled"])
