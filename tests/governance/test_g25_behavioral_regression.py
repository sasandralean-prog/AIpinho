from fastapi.testclient import TestClient

from aipinho.app_factory import create_app


def _client() -> TestClient:
    return TestClient(create_app())


def test_analysis_plan_no_write_approval_direct_chat() -> None:
    payload = _client().post(
        "/api/v1/chat",
        json={"message": "Diagnostique problemas de UX e responda com relatorio do que mudar.", "context": {"surface": "api"}},
    ).json()

    assert payload["approval_id"] is None
    assert payload["governance_lifecycle"]["intent"]["intent_type"] == "workspace_analysis_readonly"
    assert payload["governance_lifecycle"]["operation_contract"]["requested_actions"] == []


def test_multichannel_same_prompt_same_lifecycle_class() -> None:
    client = _client()
    prompt = "Analise os arquivos e crie um plano. Nao escreva arquivos."
    direct = client.post("/api/v1/chat", json={"message": prompt, "context": {"surface": "api"}}).json()
    session = client.post("/api/v1/chat/sessions", json={"title": "g25"}).json()["session"]["session_id"]
    persistent = client.post(f"/api/v1/chat/sessions/{session}/send", json={"role": "user", "content": prompt, "metadata": {}}).json()["chat_response"]
    compat = client.post("/v1/chat/completions", json={"model": "aipinho-local", "messages": [{"role": "user", "content": prompt}]}).json()

    assert direct["governance_lifecycle"]["intent"]["intent_type"] == "workspace_analysis_readonly"
    assert persistent["governance_lifecycle"]["intent"]["intent_type"] == "workspace_analysis_readonly"
    assert compat["aipinho"]["governance_lifecycle"]["intent"]["intent_type"] == "workspace_analysis_readonly"


def test_speaker_truth_no_success_before_completion() -> None:
    payload = _client().post(
        "/api/v1/chat",
        json={"message": r"Analise e corrija os problemas em C:\Users\rafae\Documents\AIpinhoTestes\App.", "context": {"surface": "api"}},
    ).json()

    assert payload["approval_id"] is None
    assert payload["governance_lifecycle"]["speaker_truth"]["can_claim_success"] is False
    assert "Nenhum ApprovalRequest de escrita foi criado" in payload["message"]
