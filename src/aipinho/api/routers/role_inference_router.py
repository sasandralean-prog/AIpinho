from __future__ import annotations

from fastapi import APIRouter

from aipinho.services.roles.role_inference_service import RoleInferenceService

router = APIRouter(prefix="/api/v1/role-inference", tags=["role-inference"])


@router.get("/status")
def get_role_inference_status() -> dict[str, object]:
    return RoleInferenceService().status()
