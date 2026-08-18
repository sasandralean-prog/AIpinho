import pytest
from pydantic import ValidationError
from aipinho.schemas.skills.contracts import SkillContract

def test_skill_contract_requires_input_contract():
    with pytest.raises(ValidationError): SkillContract(skill_id='x',namespace='x',category='x',display_name='x',purpose='x',when_to_use=[],when_not_to_use=[],output_contract={},required_context_purpose='skill_execution_future',required_capabilities=[],allowed_tools=[],forbidden_tools=[],risk_level='low',approval_required=False,validation=[],fallback={},anti_triggers=[],examples=[],failure_modes=[],events_emitted=[])
