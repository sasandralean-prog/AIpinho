from aipinho.services.tools.tool_permission_service import ToolPermissionService

def test_direct_shell_and_forbidden_tool_denied():
    result=ToolPermissionService().preview(skill_id='x',requested_tools=['shell.powershell'],contract_allowed_tools=['shell.powershell'],contract_forbidden_tools=[],granted_capabilities=['shell']); assert result.denied_tools==['shell.powershell']
