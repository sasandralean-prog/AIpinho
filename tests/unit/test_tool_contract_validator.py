from aipinho.services.tools.tool_contract_validator import ToolContractValidator

def test_direct_execution_contract_rejected():
    result=ToolContractValidator().validate({'tool_id':'x','provider':'x','display_name':'x','allowed_call_modes':['direct_execution']}); assert result['status']=='rejected'
