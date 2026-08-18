from fastapi.testclient import TestClient

from aipinho.main import app

client = TestClient(app)
PROJECT_ROOT = r"C:\Dev\AIpinho"


def test_chat_offers_readonly_analysis_without_auto_execution():
    chat = client.post("/api/v1/chat", json={"message": rf"Explique a arquitetura do projeto {PROJECT_ROOT} sem alterar nada"})
    assert chat.status_code == 200
    payload = chat.json()
    assert payload["status"] == "preview"
    action_types = {action["type"] for action in payload["next_actions"]}
    assert "run_readonly_analysis" in action_types
    assert "build_file_context" in action_types
    assert "execute_readonly" in action_types


def test_explicit_readonly_constraint_cannot_create_patch_preview():
    chat = client.post(
        "/api/v1/chat",
        json={
            "message": (
                rf'Analise em modo somente leitura os arquivos do projeto em "{PROJECT_ROOT}" '
                "e produza um resumo honesto. Nao altere arquivos."
            ),
        },
    )

    assert chat.status_code == 200
    payload = chat.json()
    assert payload["intent"]["intent_type"] == "readonly_analysis"
    assert payload["policy"]["contract_type"] == "readonly_analysis"
    assert payload["policy"]["approval_required_for"] == []
    assert payload["task_preview_id"]


def test_readonly_project_analysis_does_not_write_patch_shell_memory_or_rag():
    response = client.post("/api/v1/analysis/project", json={"workspace": PROJECT_ROOT, "max_files": 6, "max_total_bytes": 60000})
    assert response.status_code == 200
    body = response.json()
    assert body["write_enabled"] is False
    assert body["patch_enabled"] is False
    assert body["shell_enabled"] is False
    assert body["status"] in {"ok", "partial"}
    assert body["result"]["file_context"]["items"]
