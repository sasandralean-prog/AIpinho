from pathlib import Path

from fastapi.testclient import TestClient

from aipinho.main import app

client = TestClient(app)
PROJECT_ROOT = "C:\\Dev\\AIpinho"


def _report(workspace=PROJECT_ROOT, **extra):
    payload = {"workspace": workspace, "goal": extra.pop("goal", "architecture_overview")}
    payload.update(extra)
    response = client.post("/api/v1/reports/project", json=payload)
    assert response.status_code == 200
    return response.json()


def test_case_01_report_status():
    body = client.get("/api/v1/reports/status").json()
    assert body["deterministic_reports_enabled"] is True
    assert body["write_report_enabled"] is False
    assert body["artifact_preview_enabled"] is True


def test_case_02_generate_architecture_report_with_evidence():
    body = _report(limits={"max_findings": 20, "max_evidence_per_finding": 5, "max_report_chars": 12000})
    assert body["status"] in {"completed", "partial"}
    assert body["report"]["executive_summary"]
    assert body["report"]["findings"]
    assert body["write_enabled"] is False


def test_case_03_evidence_citations_are_relative_and_short():
    body = _report(limits={"max_findings": 8, "max_evidence_per_finding": 5, "max_report_chars": 12000})
    finding = body["report"]["findings"][0]
    for evidence in finding["evidence"]:
        if evidence.get("path"):
            assert not str(evidence["path"]).startswith(PROJECT_ROOT)
        if evidence.get("excerpt"):
            assert len(evidence["excerpt"]) <= 600


def test_case_04_partial_context_reports_limitations():
    body = _report(limits={"max_findings": 2, "max_evidence_per_finding": 1, "max_report_chars": 1000})
    assert body["status"] in {"partial", "completed"}
    assert body["report"]["limitations"] or body["rendered_markdown"].endswith("[report_truncated_by_response_limit]\n")


def test_case_05_finding_without_evidence_is_not_emitted():
    body = _report()
    assert all(finding["evidence"] for finding in body["report"]["findings"])


def test_case_06_pycache_fixture_finding(tmp_path):
    (tmp_path / "pkg" / "__pycache__").mkdir(parents=True)
    (tmp_path / "pkg" / "__pycache__" / "x.pyc").write_bytes(b"cache")
    body = _report(str(tmp_path), goal="codebase_overview")
    titles = [finding["title"] for finding in body["report"]["findings"]]
    assert "__pycache__ detectado" in titles


def test_case_07_policy_without_tests_fixture():
    from tempfile import TemporaryDirectory
    with TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "config" / "policies").mkdir(parents=True)
        (root / "config" / "policies" / "policy.yaml").write_text("schema_version: 1", encoding="utf-8")
        body = _report(str(root), goal="policy_audit")
    titles = [finding["title"] for finding in body["report"]["findings"]]
    assert "Policies existem sem testes aparentes" in titles


def test_case_08_forbidden_root_blocks_without_content():
    body = _report("C:\\PinhoabacaxiAI", goal="security_readonly")
    assert body["report"]["status"] in {"blocked", "partial", "degraded"}
    assert body["write_enabled"] is False


def test_case_09_secret_evidence_blocked(tmp_path):
    (tmp_path / ".env").write_text("SECRET=hidden", encoding="utf-8")
    (tmp_path / "README.md").write_text("demo", encoding="utf-8")
    body = _report(str(tmp_path))
    evidence_text = str(body["report"].get("evidence_index", []))
    assert "SECRET=hidden" not in evidence_text


def test_case_10_artifact_preview_does_not_write_file(tmp_path):
    (tmp_path / "README.md").write_text("demo", encoding="utf-8")
    body = _report(str(tmp_path))
    report_id = body["report"]["report_id"]
    target = tmp_path / "reports" / "analysis.md"
    preview = client.post("/api/v1/reports/project/preview-artifact", json={"report_id": report_id, "workspace": str(tmp_path), "target_path": "reports/analysis.md"}).json()
    assert preview["status"] == "preview_ready"
    assert preview["preview"]["requires_approval"] is True
    assert preview["preview"]["safe_to_execute"] is False
    assert not target.exists()


def test_case_11_artifact_preview_forbidden_root_blocked():
    body = _report()
    report_id = body["report"]["report_id"]
    preview = client.post("/api/v1/reports/project/preview-artifact", json={"report_id": report_id, "workspace": PROJECT_ROOT, "target_path": "C:\\PinhoabacaxiAI\\report.md"}).json()
    assert preview["status"] == "blocked"
    assert preview["preview"]["violations"]


def test_case_12_chat_report_no_file_write_next_action():
    chat = client.post("/api/v1/chat", json={"message": f"Explique a arquitetura do projeto {PROJECT_ROOT} sem alterar nada"}).json()
    action_types = {action["type"] for action in chat["next_actions"]}
    assert "run_project_report" in action_types
    assert "write_files" not in set(chat["policy"].get("allowed_actions", []))


def test_case_13_chat_artifact_report_does_not_write():
    chat = client.post("/api/v1/chat", json={"message": f"Salve a analise do projeto {PROJECT_ROOT} em reports/arquitetura.md"}).json()
    assert chat["status"] in {"preview", "needs_clarification", "blocked", "ok"}
    assert chat["policy"].get("safe_to_execute") is False


def test_case_14_patch_request_does_not_apply_patch_or_report_as_execution():
    chat = client.post("/api/v1/chat", json={"message": f"Corrija os problemas encontrados no projeto {PROJECT_ROOT}"}).json()
    assert chat["policy"]["safe_to_execute"] is False
    assert chat["status"] in {"preview", "blocked", "needs_clarification"}


def test_case_15_deterministic_findings_are_stable_for_same_context():
    first = _report(limits={"max_findings": 10, "max_evidence_per_finding": 3, "max_report_chars": 12000})
    second = _report(limits={"max_findings": 10, "max_evidence_per_finding": 3, "max_report_chars": 12000})
    first_core = [(f["title"], f["category"], f["severity"], [e.get("path") for e in f["evidence"]]) for f in first["report"]["findings"]]
    second_core = [(f["title"], f["category"], f["severity"], [e.get("path") for e in f["evidence"]]) for f in second["report"]["findings"]]
    assert first_core == second_core
