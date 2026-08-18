from fastapi.testclient import TestClient

from aipinho.main import app

client = TestClient(app)
PROJECT_ROOT = r"C:\Dev\AIpinho"


def _execute(tool_id, path="README.md", **extra):
    payload = {"tool_id": tool_id, "input": {"workspace": PROJECT_ROOT, "path": path, **extra}}
    return client.post("/api/v1/tools/execute-readonly", json=payload).json()


def test_sprint07_mandatory_readonly_execution_cases():
    status = client.get("/api/v1/tools/execution-status").json()
    assert status["read_only_execution_enabled"] is True
    assert status["write_execution_enabled"] is False
    assert status["shell_execution_enabled"] is False
    assert status["patch_apply_enabled"] is False
    assert status["git_write_enabled"] is False

    inspect = _execute("filesystem.inspect_path", "README.md")
    listing = _execute("filesystem.list_directory", ".")
    read = _execute("filesystem.read_file", "README.md")
    assert inspect["status"] == "executed_readonly"
    assert inspect["result"]["content"] is None
    assert listing["status"] == "executed_readonly"
    assert listing["result"]["metadata"]["entries_returned"] >= 1
    assert read["status"] == "executed_readonly"
    assert read["result"]["side_effects"] is False
    assert read["result"]["audit_event_id"]

    traversal = _execute("filesystem.read_file", r"..\..\Windows\system32\drivers\etc\hosts")
    outside = client.post("/api/v1/tools/execute-readonly", json={"tool_id": "filesystem.read_file", "input": {"workspace": PROJECT_ROOT, "path": r"C:\Users\rafae\.ssh\id_rsa"}}).json()
    protected = client.post("/api/v1/tools/execute-readonly", json={"tool_id": "filesystem.read_file", "input": {"workspace": r"C:\PinhoabacaxiAI", "path": "."}}).json()
    secret = _execute("filesystem.read_file", ".env")
    binary = _execute("filesystem.read_file", "tests/fixtures/sprint07_binary.zip")
    large = _execute("filesystem.read_file", "tests/fixtures/sprint07_large.txt", max_bytes=20)
    assert traversal["status"] == "blocked"
    assert "path_traversal" in traversal["result"]["violations"]
    assert outside["status"] == "blocked"
    assert "outside_workspace" in outside["result"]["violations"]
    assert protected["status"] == "blocked"
    assert "protected_root" in protected["result"]["violations"]
    assert secret["status"] == "blocked"
    assert "secret_file" in secret["result"]["violations"]
    assert binary["status"] == "blocked"
    assert "blocked_extension" in binary["result"]["violations"]
    assert large["status"] == "executed_readonly"
    assert large["result"]["content_truncated"] is True

    write = _execute("filesystem.write_file", "x.txt", content_preview="x")
    shell = _execute("shell.run_command", ".", command="echo hi")
    patch = _execute("patch.apply", ".")
    assert write["status"] == "blocked"
    assert "write_execution_disabled_this_sprint" in write["result"]["violations"]
    assert shell["status"] == "blocked"
    assert "shell_execution_disabled" in shell["result"]["violations"]
    assert patch["status"] == "blocked"
    assert "patch_apply_disabled" in patch["result"]["violations"]

    draft = client.post("/api/v1/task-drafts", json={"prompt": r"Conserte o bug no projeto C:\Dev\AIpinho"}).json()["draft"]
    preview = client.post("/api/v1/previews", json={"draft_id": draft["draft_id"]}).json()["preview"]
    approval = client.post("/api/v1/approvals", json={"preview_id": preview["preview_id"], "reason": "test"}).json()["approval"]
    client.post(f"/api/v1/approvals/{approval['approval_id']}/approve", json={"reason": "ok"})
    approved_write = client.post("/api/v1/tools/execute-readonly", json={"tool_id": "filesystem.write_file", "approval_id": approval["approval_id"], "input": {"workspace": PROJECT_ROOT, "path": "x.txt", "content_preview": "x"}}).json()
    assert approved_write["status"] == "blocked"
    assert "write_execution_disabled_this_sprint" in approved_write["result"]["violations"]

    dry_run = client.post("/api/v1/tools/dry-run", json={"tool_id": "filesystem.write_file", "input": {"path": r"C:\Dev\AIpinho\x.txt", "content_preview": "x"}}).json()
    assert dry_run["status"] == "needs_approval"
    assert dry_run["result"]["safe_to_execute"] is False

    readonly_draft = client.post("/api/v1/task-drafts", json={"prompt": r"Explique a arquitetura do projeto C:\Dev\AIpinho sem alterar nada"}).json()["draft"]
    readonly_preview = client.post("/api/v1/previews", json={"draft_id": readonly_draft["draft_id"]}).json()["preview"]
    from_preview = client.post(f"/api/v1/tools/execute-readonly/from-preview/{readonly_preview['preview_id']}", json={"tool_inputs": [{"tool_id": "filesystem.read_file", "input": {"path": "README.md"}}]}).json()
    assert from_preview["status"] == "executed_readonly"

    from_patch_read = client.post(f"/api/v1/tools/execute-readonly/from-preview/{preview['preview_id']}", json={"tool_inputs": [{"tool_id": "filesystem.read_file", "input": {"path": "README.md"}}]}).json()
    from_patch_apply = client.post(f"/api/v1/tools/execute-readonly/from-preview/{preview['preview_id']}", json={"tool_inputs": [{"tool_id": "patch.apply", "input": {"path": "."}}]}).json()
    assert from_patch_read["status"] == "executed_readonly"
    assert from_patch_apply["status"] == "blocked"

    chat = client.post("/api/v1/chat", json={"message": r"Explique a arquitetura do projeto C:\Dev\AIpinho sem alterar nada"}).json()
    assert chat["status"] == "preview"
    assert any(action["type"] == "execute_readonly" for action in chat["next_actions"])
