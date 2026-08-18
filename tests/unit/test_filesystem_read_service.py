from aipinho.schemas.tools.tool_execution import ToolExecutionRequest
from aipinho.services.tools.filesystem_read_service import FilesystemReadService


def _request(tool_id, workspace, path, **extra):
    data = {"workspace": str(workspace), "path": path}
    data.update(extra)
    return ToolExecutionRequest(tool_id=tool_id, input=data)


def test_filesystem_inspect_path(tmp_path):
    (tmp_path / "README.md").write_text("hello", encoding="utf-8")
    result = FilesystemReadService().inspect_path(_request("filesystem.inspect_path", tmp_path, "README.md"))
    assert result.status == "executed_readonly"
    assert result.content is None
    assert result.metadata["path_kind"] == "file"


def test_filesystem_list_directory_limited(tmp_path):
    for i in range(3):
        (tmp_path / f"f{i}.txt").write_text("x", encoding="utf-8")
    result = FilesystemReadService().list_directory(_request("filesystem.list_directory", tmp_path, ".", limit=2))
    assert result.status == "executed_readonly"
    assert result.metadata["entries_returned"] == 2
    assert "directory_entries_truncated" in result.warnings


def test_filesystem_read_file_text_and_truncate(tmp_path):
    (tmp_path / "long.txt").write_text("abcdef", encoding="utf-8")
    result = FilesystemReadService().read_file(_request("filesystem.read_file", tmp_path, "long.txt", max_bytes=3))
    assert result.status == "executed_readonly"
    assert result.content == "abc"
    assert result.content_truncated is True
    assert result.side_effects is False


def test_filesystem_blocks_binary_and_secret(tmp_path):
    (tmp_path / "binary.txt").write_bytes(b"\x00\x01\x02")
    (tmp_path / ".env").write_text("TOKEN=abc", encoding="utf-8")
    binary = FilesystemReadService().read_file(_request("filesystem.read_file", tmp_path, "binary.txt"))
    secret = FilesystemReadService().read_file(_request("filesystem.read_file", tmp_path, ".env"))
    assert binary.status == "blocked"
    assert "binary_file" in binary.violations
    assert secret.status == "blocked"
    assert "secret_file" in secret.violations
