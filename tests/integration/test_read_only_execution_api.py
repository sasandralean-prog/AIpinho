from fastapi.testclient import TestClient

from aipinho.main import app

client = TestClient(app)
PROJECT_ROOT = r"C:\Dev\AIpinho"


def _execute(tool_id, path="README.md", **extra):
    payload = {"tool_id": tool_id, "input": {"workspace": PROJECT_ROOT, "path": path, **extra}}
    return client.post("/api/v1/tools/execute-readonly", json=payload)


def test_execution_status_endpoint():
    response = client.get("/api/v1/tools/execution-status")
    assert response.status_code == 200
    body = response.json()
    assert body["read_only_execution_enabled"] is True
    assert body["write_execution_enabled"] is False
    assert body["shell_execution_enabled"] is False
    assert body["patch_apply_enabled"] is False


def test_execute_readonly_inspect_list_read():
    inspect = _execute("filesystem.inspect_path")
    listing = _execute("filesystem.list_directory", ".")
    read = _execute("filesystem.read_file")
    assert inspect.status_code == 200
    assert listing.status_code == 200
    assert read.status_code == 200
    assert inspect.json()["status"] == "executed_readonly"
    assert listing.json()["status"] == "executed_readonly"
    assert read.json()["status"] == "executed_readonly"
    assert "AIpinho" in read.json()["result"]["content"]


def test_execute_readonly_security_blocks():
    traversal = _execute("filesystem.read_file", r"..\Windows\system32\drivers\etc\hosts")
    protected = client.post("/api/v1/tools/execute-readonly", json={"tool_id": "filesystem.read_file", "input": {"workspace": r"C:\PinhoabacaxiAI", "path": "."}})
    write = _execute("filesystem.write_file", "x.txt", content_preview="x")
    shell = _execute("shell.run_command", ".", command="echo hi")
    patch = _execute("patch.apply", ".")
    assert traversal.json()["status"] == "blocked"
    assert "path_traversal" in traversal.json()["result"]["violations"]
    assert protected.json()["status"] == "blocked"
    assert write.json()["status"] == "blocked"
    assert shell.json()["status"] == "blocked"
    assert patch.json()["status"] == "blocked"


def test_execution_result_and_events_endpoints():
    response = _execute("filesystem.read_file")
    execution_id = response.json()["result"]["execution_id"]
    fetched = client.get(f"/api/v1/tools/executions/{execution_id}")
    events = client.get(f"/api/v1/tools/executions/{execution_id}/events")
    assert fetched.status_code == 200
    assert fetched.json()["execution"]["content"] is None
    assert events.status_code == 200
    assert events.json()["events"]
