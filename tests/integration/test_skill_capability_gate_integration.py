from aipinho.services.skills.skill_capability_resolver import SkillCapabilityResolver
from aipinho.services.skills.skill_registry_service import SkillRegistryService

def test_skill_requires_explicit_capability_subset():
    skill=SkillRegistryService().get('aipinho.patch_planner'); assert SkillCapabilityResolver().resolve(skill,[])['status']=='blocked'; assert SkillCapabilityResolver().resolve(skill,['patch_preview'])['status']=='allowed'
