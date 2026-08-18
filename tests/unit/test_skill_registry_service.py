from aipinho.services.skills.skill_registry_service import SkillRegistryService

def test_unknown_skill_blocked_by_absence():
    registry=SkillRegistryService(); assert registry.get('unknown') is None; assert registry.status()['unknown_skill_blocked'] is True
