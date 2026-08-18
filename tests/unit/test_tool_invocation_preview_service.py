from aipinho.services.tools.tool_invocation_preview_service import ToolInvocationPreviewService

def test_invocation_preview_never_executes():
    result=ToolInvocationPreviewService().preview(tool_id='browser.chrome',input_data={}); assert result.status=='blocked'; assert result.executed is False
