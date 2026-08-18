from fastapi.testclient import TestClient

from aipinho.app_factory import create_app


client = TestClient(create_app())


def test_local_model_runtime_registry_doctor_flow_is_status_only():
    status = client.get("/api/v1/models/status").json()
    assert status["real_inference_enabled"] is True
    assert status["local_model_runtime"]["registered_local_models"] == 14
    doctor = client.post("/api/v1/models/doctor/all", json={"include_trace": False})
    assert doctor.status_code == 200
    assert doctor.json()["count"] == 14
    chat_catalog = client.post("/api/v1/chat", json={"message": "Quais modelos estao disponiveis?"})
    assert chat_catalog.status_code == 200
    catalog = chat_catalog.json()
    assert catalog["real_inference"] is False
    assert "governed_auto_inference_enabled" in catalog["warnings"]
    chat_block = client.post("/api/v1/chat", json={"message": "Use o Qwen Coder agora."})
    assert chat_block.status_code == 200
    assert chat_block.json()["status"] == "preview"
    assert "direct_model_selection_requires_policy" in chat_block.json()["warnings"]
