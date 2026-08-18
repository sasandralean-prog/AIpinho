from aipinho.schemas.tools.tool_call import ToolCall
from aipinho.services.tools.tool_input_validator import ToolInputValidator
from aipinho.services.tools.tool_registry_service import ToolRegistryService


def _tool(tool_id: str):
    return ToolRegistryService().load().get_tool(tool_id)


def test_valid_input():
    result = ToolInputValidator().validate(_tool("filesystem.read_file"), ToolCall(tool_id="filesystem.read_file", input={"workspace": r"C:\Dev\AIpinho", "path": "README.md"}))
    assert result.input_valid is True


def test_missing_required_input():
    result = ToolInputValidator().validate(_tool("filesystem.write_file"), ToolCall(tool_id="filesystem.write_file", input={"content_preview": "x"}))
    assert result.input_valid is False
    assert "missing_required:path" in result.violations


def test_wrong_type_input():
    result = ToolInputValidator().validate(_tool("filesystem.read_file"), ToolCall(tool_id="filesystem.read_file", input={"workspace": r"C:\Dev\AIpinho", "path": 123}))
    assert result.input_valid is False
    assert "wrong_type:path:string" in result.violations


def test_extra_field_warns_without_blocking():
    result = ToolInputValidator().validate(_tool("filesystem.read_file"), ToolCall(tool_id="filesystem.read_file", input={"workspace": r"C:\Dev\AIpinho", "path": ".", "extra": "ok"}))
    assert result.input_valid is True
    assert "unknown_input_field:extra" in result.warnings


def test_forbidden_root_path_invalid():
    result = ToolInputValidator().validate(_tool("filesystem.read_file"), ToolCall(tool_id="filesystem.read_file", input={"workspace": r"C:\PinhoabacaxiAI", "path": "secret.txt"}))
    assert result.input_valid is False
    assert "forbidden_root" in result.violations
