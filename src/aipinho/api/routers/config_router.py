from __future__ import annotations

from fastapi import APIRouter

from aipinho.services.mobile_view_models.mobile_view_model_service import MobileViewModelService
from aipinho.utils.diagnostics import critical_config_status

router = APIRouter(prefix="/api/v1/config", tags=["config"])


@router.get("/status")
def get_config_status() -> dict[str, object]:
    status = critical_config_status()
    status["mobile_view_model"] = MobileViewModelService().status()
    return status
