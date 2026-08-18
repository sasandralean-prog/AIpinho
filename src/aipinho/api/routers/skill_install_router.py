from fastapi import APIRouter

from aipinho.schemas.skills.contracts import SkillInstallRequest
from aipinho.services.skills.skill_runtime_core import SkillInstallPreviewService, SkillManifestValidator

router = APIRouter(prefix="/api/v1/skills/install", tags=["skill-install"])


@router.post("/preview")
def preview_install(request: SkillInstallRequest):
    return SkillInstallPreviewService().preview(request).model_dump()


@router.post("/validate")
def validate_install(request: SkillInstallRequest):
    return SkillManifestValidator().validate(request)
