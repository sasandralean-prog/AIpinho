from aipinho.services.tools.tool_result_sanitizer import ToolResultSanitizer

def test_tool_result_redacts_token():
    result=ToolResultSanitizer().sanitize({'token':'secret','text':'Bearer abcdefghijklmnop'}); assert result['token']=='[REDACTED_SECRET]'; assert 'abcdefghijklmnop' not in result['text']
