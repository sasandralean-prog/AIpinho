from fastapi.testclient import TestClient

from aipinho.app_factory import create_app


def _client() -> TestClient:
    return TestClient(create_app())


def test_g26_conversation_capability_readonly_fix_and_continue_paths() -> None:
    client = _client()

    conversation = client.post("/api/v1/chat", json={"message": "Ola, responda curto.", "context": {"surface": "api"}}).json()
    capability = client.post("/api/v1/chat", json={"message": "Voce consegue executar tarefas?", "context": {"surface": "api"}}).json()
    readonly = client.post("/api/v1/chat", json={"message": "Faca uma auditoria e liste arquivos provaveis.", "context": {"surface": "api"}}).json()
    fix = client.post(
        "/api/v1/chat",
        json={"message": r"Analise e corrija os problemas em C:\Users\rafae\Documents\AIpinhoTestes\App.", "context": {"surface": "api"}},
    ).json()
    compat = client.post(
        "/v1/chat/completions",
        json={"model": "aipinho-local", "messages": [{"role": "user", "content": "Voce consegue executar tarefas?"}]},
    ).json()
    vscode = client.post(
        "/v1/integrations/vscode/actions/preview",
        json={
            "workspace_path": r"C:\Users\rafae\Documents\AIpinhoTestes",
            "action_type": "create_directory",
            "target_paths": [r"C:\Users\rafae\Documents\AIpinhoTestes\G26Preview"],
            "source": "vscode_continue",
            "reason": "g26",
        },
    ).json()

    assert conversation["status"] in {"ok", "degraded"}
    assert capability["operation_type"] == "capability_truth"
    assert readonly["approval_id"] is None
    assert readonly["governance_lifecycle"]["operation_contract"]["requested_actions"] == []
    assert fix["operation_type"] == "workspace_fix_request"
    assert fix["approval_id"] is None
    assert compat["aipinho"]["governance_lifecycle"]["intent"]["intent_type"] == "capability_truth"
    assert vscode["status"] == "pending_approval"
    assert vscode["governance_lifecycle"]["approval_gate"]["status"] == "pending_approval"
