from __future__ import annotations

from fastapi import APIRouter

from aipinho.schemas.runtime_doctor import RuntimeDoctorTestRequest
from aipinho.services.runtime_doctor import RuntimeDoctorService


router = APIRouter(prefix="/api/v1/runtime-doctor", tags=["runtime-doctor"])


@router.get("/status")
def status() -> dict[str, object]:
    return RuntimeDoctorService().status()


@router.post("/run")
def run(request: RuntimeDoctorTestRequest) -> dict[str, object]:
    return RuntimeDoctorService().run(request).model_dump(mode="json")
