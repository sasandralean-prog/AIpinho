from aipinho.services.skills.skill_contract_loader import SkillContractLoader

def test_loads_74_seed_skills():
    assert len(SkillContractLoader().load()) == 74
