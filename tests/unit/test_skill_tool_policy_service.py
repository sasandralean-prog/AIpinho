from aipinho.services.skills.skill_tool_policy_service import SkillToolPolicyService
from aipinho.services.skills.skill_registry_service import SkillRegistryService

def test_tool_not_allowed_and_forbidden_blocked():
    skill=SkillRegistryService().get('aipinho.patch_planner'); result=SkillToolPolicyService().validate(skill,['patch.apply']); assert result['status']=='blocked'
