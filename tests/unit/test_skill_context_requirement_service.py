from aipinho.services.skills.skill_context_requirement_service import SkillContextRequirementService
from aipinho.services.skills.skill_registry_service import SkillRegistryService

def test_missing_context_bundle_blocked():
    skill=SkillRegistryService().get('aipinho.context_explainer'); assert SkillContextRequirementService().validate(skill,None)['status']=='blocked'
