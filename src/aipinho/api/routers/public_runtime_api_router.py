from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from aipinho.api.routers.artifact_router import create_universal_artifact
from aipinho.schemas.artifacts.artifact_interaction_contracts import UniversalArtifactCreateRequest
from aipinho.schemas.public_runtime_api import PublicRuntimeRequest
from aipinho.services.public_runtime_api_service import PublicRuntimeAPI


router = APIRouter(prefix="/api/v1", tags=["public-runtime-api"])


def _api() -> PublicRuntimeAPI:
    return PublicRuntimeAPI()


def _request(operation: str, request: PublicRuntimeRequest) -> PublicRuntimeRequest:
    return request.model_copy(update={"operation": operation})


@router.post("/chat")
def public_chat(request: PublicRuntimeRequest) -> dict[str, object]:
    return _api().handle(_request("chat", request)).model_dump(mode="json")


@router.post("/execute")
def public_execute(request: PublicRuntimeRequest) -> dict[str, object]:
    return _api().handle(_request("execute", request)).model_dump(mode="json")


@router.post("/analyze")
def public_analyze(request: PublicRuntimeRequest) -> dict[str, object]:
    return _api().handle(_request("analyze", request)).model_dump(mode="json")


@router.post("/doctor")
def public_doctor(request: PublicRuntimeRequest) -> dict[str, object]:
    return _api().handle(_request("doctor", request)).model_dump(mode="json")


@router.post("/validate")
def public_validate(request: PublicRuntimeRequest) -> dict[str, object]:
    return _api().handle(_request("validate", request)).model_dump(mode="json")


@router.post("/artifacts")
def public_artifacts(request: dict[str, Any]) -> dict[str, object]:
    if "operation" in request or "contract" in request:
        public_request = PublicRuntimeRequest.model_validate(request)
        return _api().handle(_request("artifacts", public_request)).model_dump(mode="json")
    artifact_request = UniversalArtifactCreateRequest.model_validate(request)
    return create_universal_artifact(artifact_request)


@router.get("/runtime")
def public_runtime() -> dict[str, object]:
    return _api().runtime()


@router.get("/modules")
def public_modules() -> dict[str, object]:
    return _api().modules()


@router.get("/contracts")
def public_contracts() -> dict[str, object]:
    return _api().contracts_view()


@router.get("/version")
def public_version() -> dict[str, object]:
    return _api().version()
