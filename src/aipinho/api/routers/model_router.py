from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from aipinho.schemas.models.model_request import ModelRequest
from aipinho.services.chat.chat_model_policy_service import ChatModelPolicyService
from aipinho.services.models.capability_router_service import CapabilityRouterService
from aipinho.services.models.llama_cpp_status_service import LlamaCppStatusService
from aipinho.services.models.manual_inference_status_service import ManualInferenceStatusService
from aipinho.services.models.model_capability_detector_service import ModelCapabilityDetectorService
from aipinho.services.models.model_health_service import ModelHealthService
from aipinho.services.models.model_invocation_service import ModelInvocationService
from aipinho.services.models.model_profile_service import ModelProfileService
from aipinho.services.models.model_registry_service import ModelRegistryService
from aipinho.services.models.model_router_service import ModelRouterService
from aipinho.services.models.model_runtime_policy_service import ModelRuntimePolicyService
from aipinho.services.models.model_status_service import ModelStatusService
from aipinho.services.models.provider_registry_service import ProviderRegistryService
from aipinho.services.models.real_inference_gate_service import RealInferenceGateService
from aipinho.services.rag.vector.vector_rag_status_service import VectorRAGStatusService
from aipinho.services.roles.role_model_gate_service import RoleModelGateService
from aipinho.services.roles.role_model_status_service import RoleModelStatusService

router = APIRouter(prefix="/api/v1/models", tags=["models"])


class StubInvokeRequest(BaseModel):
    model_request: ModelRequest | None = None
    prompt: str = ""
    model_id: str = "stub.default"
    output_contract_type: str = "plain_text"
    metadata: dict[str, Any] = Field(default_factory=dict)


class CapabilityTestRequest(BaseModel):
    capability: str
    input: Any = None


@router.get("/status")
def get_model_status() -> dict[str, object]:
    llama_status = LlamaCppStatusService().status().model_dump()
    manual_status = ManualInferenceStatusService().status().model_dump()
    gate_status = RealInferenceGateService().status()
    role_model_status = RoleModelStatusService().status()
    vector_rag_status = VectorRAGStatusService().status()
    provider_status = ProviderRegistryService().status()
    model_status = ModelStatusService().status()
    registry_status = ModelRegistryService().status()
    router_status = ModelRouterService().status()
    return {
        "status": "ok",
        "default_model": registry_status.get("default_model") or router_status.get("default", {}).get("model_id") or "stub.default",
        "real_inference_enabled": bool(gate_status.get("real_inference_enabled", False) and provider_status.get("real_inference_enabled", False)),
        "controlled_role_inference_enabled": bool(role_model_status.get("enabled", False)),
        "chat_auto_role_inference": bool(role_model_status.get("chat_auto_role_inference", False)),
        "default_coding_role": role_model_status.get("default_coding_role"),
        "default_coding_model": role_model_status.get("default_coding_model"),
        "llama_cpp_provider_enabled": bool(llama_status.get("enabled")),
        "manual_inference_enabled": bool(manual_status.get("manual_inference_enabled")),
        "smoke_test_enabled": bool(manual_status.get("smoke_test_enabled")),
        "chat_model_policy": ChatModelPolicyService().status(),
        "role_model_status": role_model_status,
        "vector_rag_status": vector_rag_status,
        "embedding_runtime_enabled": bool(vector_rag_status.get("embedding_runtime_enabled", False)),
        "reranker_runtime_enabled": bool(vector_rag_status.get("reranker_runtime_enabled", False)),
        "embedding_model": vector_rag_status.get("embedding_model"),
        "reranker_model": vector_rag_status.get("reranker_model"),
        "embedding_model_chat_use_enabled": False,
        "reranker_model_chat_use_enabled": False,
        "local_model_runtime": model_status,
        "runtime_policy": ModelRuntimePolicyService().status(),
        "components": {
            "models": registry_status,
            "providers": ProviderRegistryService().status(),
            "router": router_status,
            "real_inference_gate": gate_status,
            "role_model_gate": RoleModelGateService().status(),
            "role_model_status": role_model_status,
            "vector_rag": vector_rag_status,
            "llama_cpp": llama_status,
            "manual_inference": manual_status,
        },
    }


@router.get("")
def list_models() -> dict[str, object]:
    registry = ModelRegistryService()
    providers = ProviderRegistryService().list_providers()
    provider_status = ProviderRegistryService().status()
    runtime_policy = ModelRuntimePolicyService().load_policy()
    registry_status = registry.status()
    return {
        "status": "ok",
        "default_model": registry_status.get("default_model", "stub.default"),
        "registered_local_models": len(registry.runtime_models()),
        "models": [model.model_dump() for model in registry.runtime_models()],
        "compat_models": [model.model_dump() for model in registry.compat_models()],
        "providers": [provider.model_dump() for provider in providers],
        "real_inference_enabled": bool(provider_status.get("real_inference_enabled", False)),
        "chat_model_use_enabled": bool(runtime_policy.chat_auto_use_enabled),
        "role_model_use_enabled": bool(RoleModelStatusService().status().get("enabled", False)),
    }


@router.get("/providers")
def list_providers() -> dict[str, object]:
    providers = ProviderRegistryService().list_providers()
    status = ProviderRegistryService().status()
    return {"status": "ok", "providers": [provider.model_dump() for provider in providers], "real_inference_enabled": bool(status.get("real_inference_enabled", False))}


@router.get("/providers/{provider_id}")
def get_provider(provider_id: str) -> dict[str, object]:
    provider = ProviderRegistryService().get_provider(provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="provider_not_found")
    return {"status": "ok", "provider": provider.model_dump(), "runtime_enabled": bool(provider.enabled and provider.real_inference)}


@router.get("/registry")
def get_model_registry() -> dict[str, object]:
    return CapabilityRouterService().model_registry()


@router.get("/router")
def get_model_router_rules() -> dict[str, object]:
    return CapabilityRouterService().router_rules()


@router.post("/router/test")
def test_model_router_capability(request: CapabilityTestRequest) -> dict[str, object]:
    return CapabilityRouterService().test_capability(request.capability, request.input)


@router.get("/route-preview")
def get_model_route_preview(operation_type: str = "chat", intent_type: str | None = None, source_channel: str = "api") -> dict[str, object]:
    return CapabilityRouterService().route_preview(operation_type=operation_type, intent_type=intent_type, source_channel=source_channel)


@router.get("/{model_id}/profile")
def get_model_profile(model_id: str) -> dict[str, object]:
    profile = ModelProfileService().get_profile(model_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="model_not_found")
    return {"status": "ok", "profile": profile.model_dump()}


@router.get("/{model_id}/capabilities")
def get_model_capabilities(model_id: str) -> dict[str, object]:
    model = ModelRegistryService().get_model(model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="model_not_found")
    return {"status": "ok", "capabilities": ModelCapabilityDetectorService().detect(model)}


@router.get("/{model_id}/health")
def get_model_health(model_id: str) -> dict[str, object]:
    health = ModelHealthService().health(model_id)
    if health is None:
        raise HTTPException(status_code=404, detail="model_not_found")
    return {"status": "ok", "health": health.model_dump()}


@router.post("/invoke-stub")
def invoke_stub(request: StubInvokeRequest) -> dict[str, object]:
    service = ModelInvocationService()
    if request.model_request is not None:
        response = service.invoke(request.model_request)
    else:
        response = service.invoke_stub_prompt(
            prompt=request.prompt,
            model_id=request.model_id,
            output_contract_type=request.output_contract_type,
            metadata=request.metadata,
        )
    return {"status": "ok", "response": response.model_dump(), "real_inference_enabled": False}


@router.get("/{model_id}")
def get_model(model_id: str) -> dict[str, object]:
    model = ModelRegistryService().get_model(model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="model_not_found")
    provider = ProviderRegistryService().get_provider(model.provider_id)
    decision = ModelRouterService().select_model(requested_model_id=model_id)
    return {
        "status": "ok",
        "model": model.model_dump(),
        "provider": provider.model_dump() if provider else None,
        "route_decision": decision.as_dict(),
        "llama_cpp_status": LlamaCppStatusService().status().model_dump() if model.provider_id.startswith("llama_cpp") else None,
        "real_inference_enabled": bool(model.real_inference and provider and provider.enabled and provider.real_inference),
    }
