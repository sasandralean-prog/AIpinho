from fastapi import APIRouter, HTTPException

from aipinho.services.skills.skill_runtime_core import SkillRegistryService
from aipinho.services.skills.skill_manifest_registry_service import SkillManifestRegistryService

router = APIRouter(prefix="/api/v1/skills", tags=["skills"])


@router.get("/{skill_id}")
def get_skill(skill_id: str):
    try:
        skill = SkillManifestRegistryService().get(skill_id)
        return {"status": "ok", "skill": skill.model_dump(), "source": "manifest_registry"}
    except KeyError:
        pass
    skill = SkillRegistryService().get(skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail="unknown_skill")
    return {"status": "ok", "skill": skill.model_dump(), "source": "legacy_preview_registry"}
