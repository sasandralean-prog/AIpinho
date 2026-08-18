from aipinho.services.skills.skill_anti_trigger_service import SkillAntiTriggerService
from aipinho.services.skills.skill_registry_service import SkillRegistryService

def test_anti_trigger_blocks_direct_execution():
    skill=SkillRegistryService().get('aipinho.context_explainer'); assert 'direct_execution_blocked' in SkillAntiTriggerService().blocked_reasons(skill,['direct_execution_requested'])
