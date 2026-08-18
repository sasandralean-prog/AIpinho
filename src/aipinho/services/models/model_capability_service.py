from __future__ import annotations

from aipinho.schemas.models.model_definition import ModelDefinition
from aipinho.schemas.models.model_provider import ModelProvider


class ModelCapabilityService:
    def supports(self, model: ModelDefinition, *, purpose: str | None = None, role_id: str | None = None, capability: str | None = None) -> bool:
        if capability and capability not in set(model.capabilities):
            return False
        if role_id and model.roles and role_id not in set(model.roles):
            return False
        if purpose == "project_report" and "summarization" not in set(model.capabilities) and "structured_output" not in set(model.capabilities):
            return False
        return True

    def validate_provider_match(self, model: ModelDefinition, provider: ModelProvider | None) -> dict[str, object]:
        blocked: list[str] = []
        warnings: list[str] = []
        if provider is None:
            blocked.append("provider_not_found")
        else:
            provider_capabilities = set(provider.capabilities)
            model_capabilities = set(model.capabilities)
            if provider.provider_id == "llama_cpp_embedding" and "embedding" not in model_capabilities:
                blocked.append("embedding_provider_requires_embedding_capability")
            if provider.provider_id == "llama_cpp_reranker" and "rerank" not in model_capabilities:
                blocked.append("reranker_provider_requires_rerank_capability")
            if provider.provider_id == "llama_cpp_ocr" and "ocr" not in model_capabilities:
                blocked.append("ocr_provider_requires_ocr_capability")
            if provider.provider_id == "llama_cpp_vision" and "vision" not in model_capabilities:
                blocked.append("vision_provider_requires_vision_capability")
            unsupported = sorted(model_capabilities - provider_capabilities)
            if unsupported:
                warnings.append("model_capability_not_declared_by_provider:" + ",".join(unsupported))
        return {"status": "passed" if not blocked else "blocked", "blocked_reasons": blocked, "warnings": warnings}

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "model_capability"}
