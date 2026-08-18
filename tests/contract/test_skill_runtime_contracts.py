from aipinho.services.skills.skill_runtime_service import SkillRuntimeService

def test_runtime_ownership_and_execution_boundary():
    status=SkillRuntimeService().status(); assert status['real_execution_enabled'] is False; assert status['policy_owner']=='policy_kernel'; assert SkillRuntimeService().execute('x').real_execution_performed is False
