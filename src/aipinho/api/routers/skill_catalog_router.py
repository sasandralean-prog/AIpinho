from fastapi import APIRouter

from aipinho.services.skills.skill_runtime_core import SkillCatalogService, SkillRuntimeService

router = APIRouter(prefix="/api/v1/skills", tags=["skill-catalog"])


@router.get("/status")
def skill_status():
    return SkillRuntimeService().status()


@router.get("/catalog")
def skill_catalog(category: str | None = None, status: str | None = None):
    skills = SkillCatalogService().filter(category=category, status=status)
    return {"status": "ok", "count": len(skills), "skills": [skill.model_dump() for skill in skills]}
