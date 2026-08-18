from aipinho.services.skills.skill_composer_service import SkillComposerService

def test_composition_is_preview_only():
    result=SkillComposerService().compose(['aipinho.context_explainer','aipinho.debugger_reader']); assert result.status=='preview'; assert result.execution_started is False
