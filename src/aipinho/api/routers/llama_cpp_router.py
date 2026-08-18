from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from aipinho.schemas.models.model_request import ModelRequest
from aipinho.schemas.prompts.prompt_assembly import PromptAssemblyRequest
from aipinho.schemas.prompts.prompt_message import PromptMessage
from aipinho.services.models.llama_cpp_provider import LlamaCppProvider
from aipinho.services.models.llama_cpp_status_service import LlamaCppStatusService
from aipinho.services.models.inference_runtime_service import InferenceRuntimeService
from aipinho.services.prompts.prompt_assembly_service import PromptAssemblyService

router = APIRouter(prefix="/api/v1/models/llama-cpp", tags=["llama-cpp"])


class LlamaValidateRequest(BaseModel):
    provider_id: str = "llama_cpp.local"
    model_id: str = "llama.local.placeholder"
    executable_path: str | None = None
    model_path: str | None = None


class LlamaEstimateRequest(BaseModel):
    model_id: str = "llama.local.placeholder"
    model_path: str | None = None
    ctx_size: int = 2048
    n_predict: int = 256


class LlamaInvokeRequest(BaseModel):
    model_request: ModelRequest | None = None
    prompt_assembly: dict[str, Any] | None = None
    prompt: str = ""
    model_id: str = "llama.local.placeholder"
    allow_real_inference: bool = False
    manual_mode: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


def _request_from_payload(payload: LlamaInvokeRequest) -> ModelRequest:
    if payload.model_request is not None:
        return payload.model_request
    if payload.prompt_assembly:
        assembly_request = PromptAssemblyRequest.model_validate(payload.prompt_assembly)
        preview = PromptAssemblyService().preview(assembly_request)
        request = preview.model_request
    else:
        request = ModelRequest(
            model_id=payload.model_id,
            provider_id="llama_cpp.local",
            messages=[PromptMessage(role="user", content=payload.prompt or "Llama.cpp manual invocation request.")],
            output_contract={"contract_type": "plain_text", "format": "text"},
            safety_envelope={"source": "llama_cpp_router", "rules": ["manual route only", "no tool execution"]},
            metadata={},
        )
    merged = {
        **request.metadata,
        **payload.metadata,
        "allow_real_inference": payload.allow_real_inference or bool(request.metadata.get("allow_real_inference", False)),
        "manual_mode": payload.manual_mode or bool(request.metadata.get("manual_mode", False)),
    }
    return request.model_copy(update={"provider_id": "llama_cpp.local", "metadata": merged})


@router.get("/status")
def get_llama_cpp_status() -> dict[str, object]:
    return LlamaCppStatusService().status().model_dump()


@router.post("/validate")
def validate_llama_cpp(request: LlamaValidateRequest) -> dict[str, object]:
    provider = LlamaCppProvider()
    environment = provider.validate_environment(executable_path=request.executable_path, model_path=request.model_path)
    model_request = ModelRequest(
        model_id=request.model_id,
        provider_id=request.provider_id,
        messages=[PromptMessage(role="user", content="validate llama cpp environment")],
        output_contract={"contract_type": "plain_text", "format": "text"},
        safety_envelope={"source": "validate", "rules": ["no execution"]},
        metadata={"manual_mode": False, "allow_real_inference": False},
    )
    preview = InferenceRuntimeService(llama_cpp=provider).invoke_preview(model_request)
    return {"status": environment["status"], "environment": environment, "gate_decision": preview["gate_decision"], "runtime_estimate": preview["runtime_estimate"], "process_started": False}


@router.post("/estimate")
def estimate_llama_cpp(request: LlamaEstimateRequest) -> dict[str, object]:
    estimate = LlamaCppProvider().estimate(model_path=request.model_path, ctx_size=request.ctx_size, n_predict=request.n_predict)
    return {"status": "ok", "model_id": request.model_id, "runtime_estimate": estimate, "process_started": False}


@router.post("/invoke-preview")
def invoke_preview_llama_cpp(request: LlamaInvokeRequest) -> dict[str, object]:
    model_request = _request_from_payload(request)
    preview = InferenceRuntimeService().invoke_preview(model_request)
    return preview


@router.post("/invoke")
def invoke_llama_cpp(request: LlamaInvokeRequest) -> dict[str, object]:
    model_request = _request_from_payload(request)
    response = InferenceRuntimeService().invoke(model_request)
    return {"status": response.status, "response": response.model_dump(), "process_started": response.real_inference}
