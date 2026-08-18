from aipinho.services.skills.skill_contract_validator import SkillContractValidator

def test_missing_input_contract_rejected():
    assert SkillContractValidator().validate({'skill_id':'x'})['status'] == 'rejected'
