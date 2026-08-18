import pytest
from aipinho.services.skills.skill_event_emitter import SkillEventEmitter

def test_registered_event_emits_and_unknown_blocks():
    event=SkillEventEmitter().emit('skill_preview_created','preview',{'safe':True}); assert event['event_type']=='skill_preview_created'
    with pytest.raises(ValueError): SkillEventEmitter().emit('skill_unknown','x',{})
