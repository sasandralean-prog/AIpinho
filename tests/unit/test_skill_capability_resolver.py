from aipinho.services.skills.skill_capability_resolver import SkillCapabilityResolver
from aipinho.services.skills.skill_registry_service import SkillRegistryService

def test_missing_capability_blocked():
    skill=SkillRegistryService().get('aipinho.patch_planner'); assert SkillCapabilityResolver().resolve(skill,[])['missing']==['patch_preview']
