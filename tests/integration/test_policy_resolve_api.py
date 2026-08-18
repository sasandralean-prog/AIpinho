from fastapi.testclient import TestClient

from aipinho.app_factory import create_app


def client():
    return TestClient(create_app())


def readonly_payload():
    return {
        "intent": {"intent_type": "readonly_analysis", "requires_task": True, "requires_workspace": True, "risk_level": "low", "confidence": 1.0, "evidence": []},
        "task": {"task_type": "readonly_analysis", "requested_actions": ["read_file"], "read_only": True, "approval_requested": False},
        "workspace": {"path": "C:\\Dev\\AIpinho", "declared": True},
        "role": {"role_id": "executor"},
        "user_constraints": {"read_only": False, "no_write": False, "no_shell": False, "no_network": False},
    }


def test_policy_resolve_returns_200():
    response = client().post("/api/v1/policy/resolve", json=readonly_payload())

    assert response.status_code == 200
    assert response.json()["status"] == "allowed"
    assert response.json()["canonical_source"] == "effective_policy_decision"
    assert response.json()["canonical_policy"]["permission"] == "allowed"


def test_policy_explain_returns_trace():
    response = client().post("/api/v1/policy/explain", json=readonly_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["decision"]["trace"]
    assert body["canonical_source"] == "effective_policy_decision"


def test_contract_preview_returns_safe_preview():
    response = client().post("/api/v1/policy/contract-preview", json=readonly_payload())

    assert response.status_code == 200
    assert response.json()["safe_to_preview"] is True


def test_forbidden_root_returns_denied_not_500():
    payload = readonly_payload()
    payload["workspace"]["path"] = "C:\\Windows"

    response = client().post("/api/v1/policy/resolve", json=payload)

    assert response.status_code == 200
    assert response.json()["status"] == "denied"


def test_unknown_action_returns_denied_not_500():
    payload = readonly_payload()
    payload["task"]["requested_actions"] = ["teleport_files"]

    response = client().post("/api/v1/policy/resolve", json=payload)

    assert response.status_code == 200
    assert response.json()["status"] == "denied"
