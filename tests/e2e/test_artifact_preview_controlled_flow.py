from pathlib import Path

from fastapi.testclient import TestClient

from aipinho.app_factory import create_app
from artifact_fixtures import artifact_workspace

client = TestClient(create_app())


def _payload(workspace: Path | str, target_path: str = "reports/analysis.md", content: str = "# Report\n\nOk.", fmt: str = "markdown"):
    return {
        "workspace": str(workspace),
        "target_path": target_path,
        "source": {"source_type": "user_provided_content", "format": fmt, "content": content},
        "artifact_type": "report",
        "title": "E2E artifact preview",
    }


def _create(workspace: Path | str, target_path: str = "reports/analysis.md", content: str = "# Report\n\nOk.", fmt: str = "markdown"):
    return client.post("/api/v1/artifacts/previews", json=_payload(workspace, target_path, content, fmt)).json()["preview"]


def test_artifact_preview_controlled_flow_24_cases(tmp_path):
    workspace = artifact_workspace(tmp_path)
    cases = []

    status = client.get("/api/v1/artifacts/status").json()["artifact_writer"]
    cases.append(("01_status", status["mode"], status["write_enabled"] is False, "passed"))

    valid = _create(workspace, "reports/analysis.md")
    cases.append(("02_markdown_preview", valid["status"], valid["write_allowed_now"], "passed" if valid["status"] == "needs_approval" and valid["write_allowed_now"] is False else "failed"))

    task_missing = client.post("/api/v1/artifacts/previews/from-task-run/missing", json={"workspace": str(workspace), "target_path": "reports/task.md"}).json()["preview"]
    cases.append(("03_taskrun_missing_blocks", task_missing["status"], task_missing["blocked_reasons"], "passed" if task_missing["status"] == "blocked" else "failed"))

    json_valid = _create(workspace, "exports/result.json", '{"ok": true}', "json")
    cases.append(("04_json_valid", json_valid["validation"]["content"]["format_valid"], json_valid["status"], "passed" if json_valid["validation"]["content"]["format_valid"] else "failed"))

    json_invalid = _create(workspace, "exports/result.json", "{bad", "json")
    cases.append(("05_json_invalid", json_invalid["status"], json_invalid["blocked_reasons"], "passed" if json_invalid["status"] == "blocked" else "failed"))

    outside_allowed_root = tmp_path / "outside_allowed_root"
    outside_allowed_root.mkdir()
    forbidden = _create(outside_allowed_root, "reports/report.md")
    cases.append(("06_forbidden_root", forbidden["status"], forbidden["blocked_reasons"], "passed" if "workspace_root_not_allowed" in forbidden["blocked_reasons"] else "failed"))

    traversal = _create(workspace, "reports/../../src/hack.md")
    cases.append(("07_path_traversal", traversal["status"], traversal["blocked_reasons"], "passed" if "path_traversal" in traversal["blocked_reasons"] else "failed"))

    source_code = _create(workspace, "reports/fix.py")
    cases.append(("08_source_code_extension", source_code["status"], source_code["blocked_reasons"], "passed" if "source_code_target" in source_code["blocked_reasons"] else "failed"))

    config_target = _create(workspace, "config/policies/x.yaml", "schema_version: 1", "yaml")
    cases.append(("09_config_target", config_target["status"], config_target["blocked_reasons"], "passed" if "config_mutation_target" in config_target["blocked_reasons"] else "failed"))

    script_target = _create(workspace, "reports/run.ps1")
    cases.append(("10_script_extension", script_target["status"], script_target["blocked_reasons"], "passed" if "script_target" in script_target["blocked_reasons"] else "failed"))

    secret = _create(workspace, "reports/secret.md", "api_key=abc123")
    cases.append(("11_secret_content", secret["status"], secret["blocked_reasons"], "passed" if "secret_content" in secret["blocked_reasons"] else "failed"))

    binary = _create(workspace, "reports/binary.md", "\u0000")
    cases.append(("12_binary_content", binary["status"], binary["blocked_reasons"], "passed" if "binary_content" in binary["blocked_reasons"] else "failed"))

    (workspace / "reports" / "existing.md").write_text("old", encoding="utf-8")
    existing = _create(workspace, "reports/existing.md", "new")
    cases.append(("13_existing_diff", existing["would_overwrite"], existing["diff"]["available"], "passed" if existing["would_overwrite"] and existing["diff"]["available"] else "failed"))

    (workspace / "reports" / "existing_secret.md").write_text("api_key=abc123", encoding="utf-8")
    existing_secret = _create(workspace, "reports/existing_secret.md", "new")
    cases.append(("14_existing_secret_no_leak", existing_secret["diff"]["available"], existing_secret["diff"]["warnings"], "passed" if "existing_target_secret_not_read" in existing_secret["diff"]["warnings"] else "failed"))

    large = _create(workspace, "reports/large.md", "x" * 90000)
    cases.append(("15_large_content", large["status"], large["blocked_reasons"], "passed" if "content_too_large" in large["blocked_reasons"] else "failed"))

    approval = client.post(f"/api/v1/artifacts/previews/{valid['preview_id']}/request-approval").json()
    cases.append(("16_approval_request", approval["approval"]["status"], approval["preview"]["status"], "passed" if approval["approval"]["status"] == "pending" else "failed"))

    approved = client.post(f"/api/v1/approvals/{approval['approval']['approval_id']}/approve", json={"reason": "test"}).json()
    fetched = client.get(f"/api/v1/artifacts/previews/{valid['preview_id']}").json()["preview"]
    cases.append(("17_approval_does_not_write", approved["approval"]["execution_status"], Path(workspace / "reports" / "analysis.md").exists(), "passed" if fetched["status"] == "approved_for_future_write" and not Path(workspace / "reports" / "analysis.md").exists() else "failed"))

    blocked_approval = client.post(f"/api/v1/artifacts/previews/{source_code['preview_id']}/request-approval")
    cases.append(("18_blocked_no_approval", blocked_approval.status_code, blocked_approval.json()["detail"], "passed" if blocked_approval.status_code == 409 else "failed"))

    refreshed = client.post(f"/api/v1/artifacts/previews/{existing['preview_id']}/refresh-validation").json()["preview"]
    cases.append(("19_refresh_validation", refreshed["would_overwrite"], refreshed["write_allowed_now"], "passed" if refreshed["would_overwrite"] and refreshed["write_allowed_now"] is False else "failed"))

    chat_save = client.post("/api/v1/chat", json={"message": "Salve esse relatorio em reports/chat.md", "context": {"active_workspace": str(workspace), "surface": "api"}}).json()
    cases.append(("20_chat_save_preview", chat_save["status"], chat_save["next_actions"], "passed" if chat_save["status"] == "preview" else "failed"))

    chat_now = client.post("/api/v1/chat", json={"message": "Pode gravar agora", "context": {"active_workspace": str(workspace), "surface": "api"}}).json()
    cases.append(("21_chat_write_now_no_auto_write", chat_now["status"], chat_now["warnings"], "passed" if chat_now["status"] in {"blocked", "preview"} and "chat_does_not_auto_write_files" in chat_now["warnings"] else "failed"))

    chat_src = client.post("/api/v1/chat", json={"message": "Salve em src/main.py", "context": {"active_workspace": str(workspace), "surface": "api"}}).json()
    cases.append(("22_chat_source_code_target", chat_src["status"], chat_src["warnings"], "passed" if chat_src["status"] in {"blocked", "needs_clarification"} else "failed"))

    report_missing = client.post("/api/v1/artifacts/previews/from-report/project_report_missing", json={"workspace": str(workspace), "target_path": "reports/missing.md"}).json()["preview"]
    cases.append(("23_failed_report_source", report_missing["status"], report_missing["blocked_reasons"], "passed" if report_missing["status"] == "blocked" else "failed"))

    forbidden_files = [workspace / "reports" / name for name in ["analysis.md", "chat.md", "task.md", "missing.md"]]
    cases.append(("24_no_workspace_side_effects", "checked", [path.exists() for path in forbidden_files], "passed" if not any(path.exists() for path in forbidden_files) else "failed"))

    assert len(cases) == 24
    failures = {case[0]: case for case in cases if case[3] != "passed"}
    assert not failures
