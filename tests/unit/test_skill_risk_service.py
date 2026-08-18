from aipinho.services.skills.skill_risk_service import SkillRiskService
from aipinho.services.skills.skill_registry_service import SkillRegistryService

def test_high_risk_requires_approval():
    skill=SkillRegistryService().get('aipinho.patch_planner'); assert SkillRiskService().evaluate(skill)['approval_required'] is True
