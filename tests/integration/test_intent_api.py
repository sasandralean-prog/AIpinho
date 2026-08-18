from fastapi.testclient import TestClient

from aipinho.app_factory import create_app


def client():
    return TestClient(create_app())


def analyze(prompt: str):
    response = client().post("/api/v1/intent/analyze", json={"prompt": prompt, "context": {}})
    assert response.status_code == 200
    return response.json()["intent_map"]


def test_intent_status_200():
    response = client().get("/api/v1/intent/status")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_intent_taxonomy_200():
    response = client().get("/api/v1/intent/taxonomy")

    assert response.status_code == 200
    assert "conversation" in response.json()["taxonomy"]


def test_intent_analyze_200():
    intent = analyze("Explique sua arquitetura atual")

    assert intent["intent_type"] == "self_analysis"


def test_mandatory_api_cases():
    expected = {
        "Bom dia, tudo certo?": "conversation",
        "O que voce consegue fazer?": "capability_explanation",
        "Faça um report final desta conversa": "in_chat_final_report",
        "Salve um relatório em reports/final.md": "artifact_generation",
        "Conserte o bug no projeto C:\\Dev\\AIpinho": "patch_request",
    }
    for prompt, intent_type in expected.items():
        assert analyze(prompt)["intent_type"] == intent_type


def test_forbidden_root_api_case():
    intent = analyze("Corrija C:\\PinhoabacaxiAI")

    assert intent["workspace"]["protected"] is True
    assert intent["risk"]["level"] == "critical"