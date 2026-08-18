from aipinho.services.skills.skill_output_validator import SkillOutputValidator

def test_output_accepts_summary_and_rejects_missing():
    service=SkillOutputValidator(); assert service.validate('aipinho.context_explainer',{'summary':'ok'}).accepted; assert not service.validate('aipinho.context_explainer',{}).accepted
